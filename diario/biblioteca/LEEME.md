# Biblioteca de Cacique Diario · message library

Each file is one theme (`tema`). Each message:

| field | meaning |
|---|---|
| `id` | unique, never change it once used (the history uses it) |
| `es`, `en` | the message, Spanish first. Keep it short: it must fit a mirror or a photo frame |
| `para` | who it's for: `todos` (anyone, shared screens), `adultos`, `esposo`, `esposa`, `padres`, `abuelos`, `hijos` |
| `fuente` | where it comes from (a verse reference, a book, "Cacique") |
| `verificar` | `true` = starts **pending** in the approval page until an adult checks it (all Bible verses) |

Shared screens (frames, TV, kitchen) only show `todos` messages. Personal screens (`?para=<person>`) also show
the messages for that person's roles.

Bible text: Reina-Valera 1909 (Spanish) and King James Version (English), both public domain, spelling modernized.
Compare with your own Bible before approving.

Add your own messages in the approval page (**Mis mensajes**); they're saved on the server, not here.
