#!/usr/bin/python3

# noinspection PyUnresolvedReferences,PyProtectedMember
from brownie import VaccinationCenterRegistry, accounts


def main():
    return VaccinationCenterRegistry.deploy({'from': accounts[0]})
