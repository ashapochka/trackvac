# TrackVac

A prototype of the Ethereum/Quorum smart contract application demonstrating the concept of international consortium enforcing COVID-19 vaccination rules for travelers crossing national borders and required to be vaccinated for country entrance.

## Installation

1. Make sure your Python 3 is recent (3.8+) and [install Poetry](https://python-poetry.org/docs/#installation), if you haven't already.

2. Make sure you have Node.js and [install Ganache CLI](https://www.npmjs.com/package/ganache-cli).
   ```bash
   npm install -g ganache-cli
   ```

3. To install project dependencies enter its root directory and run:
   ```bash
   poetry install
   ```
   
4. Switch to the project's virtual environment:
   ```bash
   poetry shell
   ```

## Testing

To run the tests:

```bash
brownie test
```

The unit tests included in this prototype demonstrate scenarios of registration and validation of the vaccination certificates by running the smart contracts inside Ganache.

## Resources

* Check out my medium post [TrackVac — Track COVID-19 Vaccination on Blockchain](https://medium.com/techtale/trackvac-track-covid-19-vaccination-on-blockchain-bb0d492d66d4) describing the concepts and architecture behind this prototype.


Any questions? Reach to me by submitting an issue for this repository.

## License

This project is licensed under the [MIT license](LICENSE).
