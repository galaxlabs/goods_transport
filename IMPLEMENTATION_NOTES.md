# Goods Transport Implementation Notes

## Phase
- Backend foundation

## Scope implemented
- Created `goods_transport` Frappe app scaffold
- Added tenant foundation services and permission helpers
- Added bootstrap role setup hooks
- Added initial tenant/profile APIs
- Added Step 2 foundation DocTypes:
  - `Transport Tenant`
  - `Tenant Branch`
  - `Tenant User Profile`
  - `Commodity Customer`
  - `Vehicle Owner`
  - `Transport Driver`
  - `Transport Vehicle`
- Added validation for tenant presence and per-tenant vehicle-number uniqueness
- Added focused tests for tenant resolution and vehicle uniqueness
- Added Phase 1 tenant settings DocTypes:
  - `Tenant Print Setting`
  - `Tenant WhatsApp Setting`
  - `Tenant Google Map Setting`
- Added secure tenant settings APIs:
  - `get_tenant_print_settings`
  - `update_tenant_print_settings`
  - `get_whatsapp_settings`
  - `update_whatsapp_settings`
  - `get_map_settings`
  - `update_map_settings`
- Added focused tests for tenant-derived settings updates and hidden password fields
- Added tenant onboarding APIs:
  - `register_transport_company`
  - `register_customer`
  - `register_driver`
  - `register_vehicle_owner`
  - `register_vehicle`
- Added onboarding service helpers for tenant-safe record creation, tenant admin profile creation, and optional portal user linking

## Site target
- `gt.digigalaxy.cloud`

## Notes
- ERPNext was later installed on the same site, so transport-owned `Driver` and `Vehicle` were renamed to `Transport Driver` and `Transport Vehicle` to avoid collisions with ERPNext Setup DocTypes.
- `default_currency` is currently a `Data` field to keep the clean Frappe-only site independent from ERPNext-only master doctypes.
- The `Transport Vehicle` DocType uses fieldname `vehicle_owner` with label `Owner` because Frappe reserves `owner` as a system column.
- Tenant settings APIs resolve tenant from the logged-in tenant profile for normal users; only global users can pass an explicit tenant.
- Onboarding APIs for tenant-owned records resolve tenant from the logged-in tenant profile for normal tenant users, preventing frontend tenant spoofing.
- `register_transport_company` is guest-enabled for first tenant/admin onboarding.
- Password fields for Twilio and Google Maps are write-only through the API response layer.
- Further phases can safely extend the current service layout under `goods_transport/services/` and `goods_transport/api/`.

## Latest verification
- `bench --site gt.digigalaxy.cloud migrate`
- `bench --site gt.digigalaxy.cloud run-tests --app goods_transport`
- Result: 11 tests passing
