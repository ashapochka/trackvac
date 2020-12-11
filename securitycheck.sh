docker run \
  -v "$(pwd)":/tmp mythril/myth \
  analyze \
  /tmp/contracts/VaccinationRegistry.sol \
  --solv 0.6.0 --execution-timeout 100
