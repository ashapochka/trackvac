#!/usr/bin/python3

import pytest


@pytest.fixture(scope="function", autouse=True)
def isolate(fn_isolation):
    # perform a chain rewind after completing each test,
    # to ensure proper isolation
    # https://eth-brownie.readthedocs.io/en/v1.10.3/tests-pytest-intro.html#isolation-fixtures
    pass


@pytest.fixture(scope="module")
def vcr(VaccinationCenterRegistry, accounts):
    return VaccinationCenterRegistry.deploy({'from': accounts[0]})


@pytest.fixture(scope="module")
def var(VaccinationAcceptanceRules, accounts):
    return VaccinationAcceptanceRules.deploy({'from': accounts[0]})


@pytest.fixture(scope="module")
def vr(VaccinationRegistry, accounts, vcr, var):
    return VaccinationRegistry.deploy(vcr, var, {'from': accounts[0]})
