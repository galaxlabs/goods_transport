# Goods Transport

Pakistan goods transport and warehouse management SaaS built as a Frappe app.

## What’s included

- Tenant foundation and onboarding APIs
- Transport tenant, branch, user profile, driver, vehicle, load, and settings DocTypes
- Tenant-safe permission helpers and service layer organization
- Focused backend tests for onboarding, tenant foundation, and tenant settings

## Installation

Install this app with the [Bench](https://github.com/frappe/bench) CLI:

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app https://github.com/galaxlabs/goods_transport.git --branch main
bench install-app goods_transport
```

## Development

Enable formatting and linting hooks after cloning:

```bash
cd apps/goods_transport
pre-commit install
```

Pre-commit is configured with:

- `ruff`
- `eslint`
- `prettier`
- `pyupgrade`

## Verification

Most recent local verification recorded in `IMPLEMENTATION_NOTES.md`:

- `bench --site gt.digigalaxy.cloud migrate`
- `bench --site gt.digigalaxy.cloud run-tests --app goods_transport`

## License

MIT
