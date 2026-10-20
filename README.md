### Vmmsx

Dynamic approach to the VMMS application

### Installation

You can install this app using the [bench](https://github.com/frappe/bench) CLI:

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app $URL_OF_THIS_REPO --branch develop
bench install-app vmmsx
```

### Contributing

This app uses `pre-commit` for code formatting and linting. Please [install pre-commit](https://pre-commit.com/#installation) and enable it for this repository:

```bash
cd apps/vmmsx
pre-commit install
```

Pre-commit is configured to use the following tools for checking and formatting your code:

- ruff
- eslint
- prettier
- pyupgrade

### License

mit

### Profession register

Fresh installs and upgrades seed 684 profession options from the reviewed
2026-10-20 legacy register export. Extra whitespace is collapsed to match
migration lookup targets. Existing professions and profile links are preserved;
the setup adds only missing options. Existing sites receive the options during
`bench --site <site> migrate`; no browser script is required.
