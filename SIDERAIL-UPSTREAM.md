# Official SideRail runtime in POMP NET MOHAMMAD

The production Dockerfile builds the original upstream SideRail repository at the pinned commit:

- Upstream: https://github.com/icubaby/SideRail
- Pinned commit: `6d794ce2303a01ecc412941a4f38fd00a3bda65b`
- Production UI: upstream React SPA, built from the pinned source without POMP NET theme, branding, or i18n patch scripts.
- Production API/core: upstream SideRail Express server and its Xray lifecycle.
- Public app port: `8080`; health endpoint: `/healthz`.
- Upstream `LICENSE`, `NOTICE`, and `README.md` are copied into the image and are not stripped.

## Data preservation

The Docker image does not delete or overwrite the former Marzban database. The default SideRail data directory is a separate folder, `/var/lib/marzban/siderail`, under the existing persistent volume mount `/var/lib/marzban`. SideRail creates its own `siderail.db` and `core/` there. Existing Marzban files remain in place but are not automatically imported into SideRail. Do not remove or recreate the Railway Volume.

## Important deployment notes

1. Keep the existing Railway Volume mounted at `/var/lib/marzban`; without it, SideRail data will be ephemeral.
2. Set or retain a strong `JWT_SECRET` as a Railway secret, or allow SideRail to create and persist its own secret file in the data directory.
3. The first SideRail setup/admin account is created through the original SideRail setup flow.
4. This source change does not itself create a Railway project, select a paid plan, or deploy the service.
5. CI image-build success is not a claim that the live Railway service or external VLESS traffic has been verified.

The upstream author attribution and all upstream license/notice files remain preserved. The upstream application source is not patched or rebranded in this production build.
