from datetime import datetime, date, timedelta
from typing import Optional, List

import brownie
from eth_utils import keccak
from web3 import Web3

from pydantic import BaseModel


class Vaccine(BaseModel):
    code_type: str
    code: str


class VaccinationCenter(BaseModel):
    id: int
    name: str
    address: str


class Person(BaseModel):
    full_name: str
    passport_number: str
    birthdate: date
    nationality: str


class VaccinationCertificate(BaseModel):
    center_id: int
    vaccination_time: datetime
    vaccine: Vaccine
    person: Optional[Person]
    person_id: Optional[str]
    proof: Optional[str]


def hash_person(person: Person):
    person_json = person.json()
    person_hash = Web3.toHex(keccak(text=person_json))
    return person_hash


jane_smith = Person(
    full_name='Jane Smith',
    passport_number='FP123456789',
    birthdate=date.fromisoformat('1999-02-15'),
    nationality='Nagonia'
)

john_doe = Person(
    full_name='John Doe',
    passport_number='FP987654321',
    birthdate=date.fromisoformat('1980-05-02'),
    nationality='Nagonia'
)

coronavac = Vaccine(
    code_type='IVT',
    code='CoronaVac'
)

sputnikvac = Vaccine(
    code_type='RF',
    code='SputnikVac'
)


def municipal_vac_12(address) -> VaccinationCenter:
    return VaccinationCenter(
        id=1234567890,
        name='Municipal Vac #12, Nagonia',
        address=str(address)
    )


def fake_center(address) -> VaccinationCenter:
    return VaccinationCenter(
        id=666,
        name='Fake Vaccines',
        address=str(address)
    )


def compute_person_id(contract, person):
    return Web3.toHex(contract.computePersonId(
        person.full_name,
        person.birthdate.isoformat(),
        person.passport_number,
        person.nationality
    ))


def certify_vaccination(
        contract,
        center: VaccinationCenter,
        person: Person,
        vaccine: Vaccine,
        vaccination_time: datetime = None
):
    return VaccinationCertificate(
        center_id=center.id,
        vaccination_time=(vaccination_time or
                          datetime.fromisoformat('2020-12-01 12:00:00')),
        vaccine=vaccine,
        person=person,
        person_id=compute_person_id(contract, person)
    )


def register_certificate(
        contract,
        center: VaccinationCenter,
        certificate: VaccinationCertificate,
        center_address: str = None
):
    tx = contract.registerVaccination(
        certificate.center_id,
        int(certificate.vaccination_time.timestamp()),
        certificate.vaccine.code_type,
        certificate.vaccine.code,
        certificate.person_id,
        {
            'from': center_address or center.address
        }
    )
    certificate.proof = tx.return_value
    return certificate


def register_center(contract, center: VaccinationCenter):
    return contract.registerCenter(
        center.id, center.name,
        center.address
    )


def register_rules(
        contract,
        area: str,
        time_before_departure: timedelta,
        vaccines: List[Vaccine]
):
    contract.registerRules(
        area, time_before_departure.total_seconds(),
        [[v.code_type, v.code] for v in vaccines]
    )


def validate_vaccination(
        vr,
        area: str, departure_time: datetime,
        certificate_proof: str, person_id: str,
        validator_address: str
):
    vr.validateVaccination(
        area, int(departure_time.timestamp()),
        certificate_proof, person_id,
        {'from': validator_address}
    )


def test_register_rules(var):
    register_rules(var, 'area1', timedelta(days=30), [coronavac])


def test_compute_person_id(vr):
    """
    anyone can compute person's id by the available personal data using
    the same comutation rules across legislations

    :param vr:
    :return:
    """
    person_id = compute_person_id(vr, jane_smith)
    assert person_id
    assert len(person_id) == 66


def test_register_center(vcr, accounts):
    """
    any center certifying vaccinations must be officially registered

    :param vcr:
    :return:
    """
    center = municipal_vac_12(accounts[1])
    register_center(vcr, center)
    registered_center = vcr.centers.call(center.id)
    assert registered_center[0] is True
    assert registered_center[1] == center.name
    assert registered_center[2] == center.address


def test_register_vaccination(vcr, vr, accounts):
    """
    a trusted registered center can successfully register its vaccinations

    :param vcr:
    :param vr:
    :return:
    """
    center = municipal_vac_12(accounts[1])
    register_center(vcr, center)
    certificate = certify_vaccination(
        vr, center, jane_smith, coronavac
    )
    register_certificate(vr, center, certificate)
    assert certificate.proof
    vac = vr.vaccinations.call(certificate.proof)
    assert vac[0] is True
    assert vac[1] == certificate.center_id
    assert vac[2] == certificate.vaccination_time.timestamp()
    assert vac[3] == certificate.vaccine.code_type
    assert vac[4] == certificate.vaccine.code
    assert vac[5] == certificate.person_id


def test_register_vaccination_fails_center_not_registered(vr, accounts):
    """
    fake vaccination registration fails because the fake center is not
    registered.

    :param vr:
    :return:
    """
    center = fake_center(accounts[2])
    certificate = certify_vaccination(
        vr, center, jane_smith, coronavac
    )
    # noinspection PyUnresolvedReferences
    with brownie.reverts("Validated center is not registered"):
        register_certificate(vr, center, certificate)


def test_register_vaccination_fails_center_address_invalid(vcr, vr, accounts):
    """
    tests the case, when a fake center pretends to be a valid center
    using its registration information but fails certificate registration
    from a fake address (the valid account will be locked without knowing
    a password in the realistic deployment)

    :param vcr:
    :param vr:
    :return:
    """
    center = municipal_vac_12(accounts[1])
    fake_address = accounts[2]
    register_center(vcr, center)
    certificate = certify_vaccination(
        vr, center, jane_smith, coronavac
    )
    # noinspection PyUnresolvedReferences
    with brownie.reverts(
            "Registered center's address is different from the passed address"
    ):
        register_certificate(
            vr, center, certificate,
            center_address=fake_address
        )


def test_validate_vaccination(vcr, var, vr, accounts):
    vac_center = municipal_vac_12(accounts[1])
    arrival_area = 'Garivas'
    time_before_departure = timedelta(days=30)
    accepted_vaccines = [coronavac]
    traveler = jane_smith
    vac_time = datetime.fromisoformat('2020-12-10 11:30')
    vaccine = accepted_vaccines[0]
    departure_time = vac_time + timedelta(days=10)
    airport_address = accounts[3]

    # register vaccination centers and validation rules as a prerequisite
    # to scenario execution
    register_center(vcr, vac_center)
    register_rules(var, arrival_area, time_before_departure, accepted_vaccines)

    # vaccination center vaccinates the traveler and registers
    # traveler's vaccination certificate
    certificate = certify_vaccination(
        vr, vac_center, traveler, vaccine, vaccination_time=vac_time
    )
    register_certificate(vr, vac_center, certificate)

    # an airport where the traveler either departs from or arrives in
    # validates the vaccination certificate presented by the traveler
    traveler_id = compute_person_id(vr, traveler)
    validate_vaccination(
        vr, arrival_area, departure_time,
        certificate.proof, traveler_id,
        airport_address
    )


def test_validate_vaccination_fails_proof_invalid(vcr, var, vr, accounts):
    arrival_area = 'Garivas'
    vac_time = datetime.fromisoformat('2020-12-10 11:30')
    departure_time = vac_time + timedelta(days=10)
    airport_address = accounts[3]

    # an airport where the traveler either departs from or arrives in
    # validates the vaccination certificate presented by the traveler
    # validation is failed because the certificate is not registered
    # on the ledger
    certificate_proof = '0x0'
    traveler_id = '0x0'
    # noinspection PyUnresolvedReferences
    with brownie.reverts(
            "Vaccination is not registered"
    ):
        validate_vaccination(
            vr, arrival_area, departure_time,
            certificate_proof, traveler_id,
            airport_address
        )


def test_validate_vaccination_fails_traveler_mismatch(vcr, var, vr, accounts):
    vac_center = municipal_vac_12(accounts[1])
    arrival_area = 'Garivas'
    time_before_departure = timedelta(days=30)
    accepted_vaccines = [coronavac]
    certified_traveler = jane_smith
    validated_traveler = john_doe
    vac_time = datetime.fromisoformat('2020-12-10 11:30')
    vaccine = accepted_vaccines[0]
    departure_time = vac_time + timedelta(days=10)
    airport_address = accounts[3]

    # register vaccination centers and validation rules as a prerequisite
    # to scenario execution
    register_center(vcr, vac_center)
    register_rules(var, arrival_area, time_before_departure, accepted_vaccines)

    # vaccination center vaccinates the traveler and registers
    # traveler's vaccination certificate
    certificate = certify_vaccination(
        vr, vac_center, certified_traveler, vaccine, vaccination_time=vac_time
    )
    register_certificate(vr, vac_center, certificate)

    # an airport where the traveler either departs from or arrives in
    # validates the vaccination certificate presented by the traveler
    # validation fails as the actual traveler mismatches certified traveler
    traveler_id = compute_person_id(vr, validated_traveler)
    # noinspection PyUnresolvedReferences
    with brownie.reverts(
            "Vaccinated person mismatch is detected"
    ):
        validate_vaccination(
            vr, arrival_area, departure_time,
            certificate.proof, traveler_id,
            airport_address
        )


def test_validate_vaccination_fails_vaccination_old(vcr, var, vr, accounts):
    vac_center = municipal_vac_12(accounts[1])
    arrival_area = 'Garivas'
    time_before_departure = timedelta(days=30)
    accepted_vaccines = [coronavac]
    traveler = jane_smith
    vac_time = datetime.fromisoformat('2020-12-10 11:30')
    vaccine = accepted_vaccines[0]
    departure_time = vac_time + timedelta(days=40)
    airport_address = accounts[3]

    # register vaccination centers and validation rules as a prerequisite
    # to scenario execution
    register_center(vcr, vac_center)
    register_rules(var, arrival_area, time_before_departure, accepted_vaccines)

    # vaccination center vaccinates the traveler and registers
    # traveler's vaccination certificate
    certificate = certify_vaccination(
        vr, vac_center, traveler, vaccine, vaccination_time=vac_time
    )
    register_certificate(vr, vac_center, certificate)

    # an airport where the traveler either departs from or arrives in
    # validates the vaccination certificate presented by the traveler
    # validation is failed because vaccination is too old
    traveler_id = compute_person_id(vr, traveler)
    # noinspection PyUnresolvedReferences
    with brownie.reverts(
            "Vaccination time is too far in the past"
    ):
        validate_vaccination(
            vr, arrival_area, departure_time,
            certificate.proof, traveler_id,
            airport_address
        )


def test_validate_vaccination_fails_vaccine_not_accepted(
        vcr, var, vr, accounts
):
    vac_center = municipal_vac_12(accounts[1])
    arrival_area = 'Garivas'
    time_before_departure = timedelta(days=30)
    accepted_vaccines = [coronavac]
    traveler = jane_smith
    vac_time = datetime.fromisoformat('2020-12-10 11:30')
    vaccine = sputnikvac
    departure_time = vac_time + timedelta(days=15)
    airport_address = accounts[3]

    # register vaccination centers and validation rules as a prerequisite
    # to scenario execution
    register_center(vcr, vac_center)
    register_rules(var, arrival_area, time_before_departure, accepted_vaccines)

    # vaccination center vaccinates the traveler and registers
    # traveler's vaccination certificate
    certificate = certify_vaccination(
        vr, vac_center, traveler, vaccine, vaccination_time=vac_time
    )
    register_certificate(vr, vac_center, certificate)

    # an airport where the traveler either departs from or arrives in
    # validates the vaccination certificate presented by the traveler
    # validation is failed because the vaccine is not on the accepted list
    traveler_id = compute_person_id(vr, traveler)
    # noinspection PyUnresolvedReferences
    with brownie.reverts(
            "The used vaccine is not accepted in the area"
    ):
        validate_vaccination(
            vr, arrival_area, departure_time,
            certificate.proof, traveler_id,
            airport_address
        )
