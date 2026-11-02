---
title_es: La red del futuro (VLANs)
title_en: The future network (VLANs)
icon: 🌐
---
<!-- ES -->
## La idea en una frase
Un solo cable, **varias redes privadas separadas**. Eso es una **VLAN**: como varios carriles en la misma carretera, cada uno con su propia regla.

| Red | Quién | ¿Internet? |
|---|---|---|
| **Cacique-Familia** | Niños, invitados | Solo el Home Lab (y sitios permitidos) |
| **Cacique-Adultos** | Adultos | Internet completo (por el Deeper Mini) |
| **Cacique-IoT** | Luces Hue, aparatos inteligentes | **No**. Solo hablan con CaciqueHome |
| **Gestión** | Administrador | Acceso a la configuración del rack |

**Recorrido:** Módem → Deeper Mini → Firewall (OPNsense, en el rack) → switch → fibra → casa → puntos de acceso Wi‑Fi (uno por área), que transmiten las cuatro redes.

El plan completo, con números de VLAN, direcciones, reglas del firewall, equipo y la caseta, está en `docs/network-plan.md` en GitHub.

<!-- EN -->
## The idea in one sentence
One cable, **several separate private networks**. That's a **VLAN**: like several lanes on the same road, each with its own rules.

| Network | Who | Internet? |
|---|---|---|
| **Cacique-Familia** | Kids, guests | Home Lab only (plus allowed sites) |
| **Cacique-Adultos** | Adults | Full internet (through the Deeper Mini) |
| **Cacique-IoT** | Hue lights, smart devices | **No**. They only talk to CaciqueHome |
| **Management** | Administrator | Access to the rack's settings |

**Path:** Modem → Deeper Mini → Firewall (OPNsense, in the rack) → switch → fiber → house → Wi‑Fi access points (one per area), broadcasting all four networks.

The full plan, with VLAN numbers, addresses, firewall rules, equipment and the shed, is in `docs/network-plan.md` on GitHub.
