# Readwise Books verification

The feature is under development on `feat/readwise-books-sync`, based on upstream
Almanac commit `360a4cd29a46115f0db9cb26a07f3c2b16e9e76e` (0.4.0).

Recorded host checks:

- Python setup tests: exact/ambiguous matching, missing-book policy, preserving
  Almanac credentials and other sidecar fields, account ownership checks, and
  immutable routing for old sessions.
- CrossPoint adapter host tests: duration/progress conversion, no-feed request,
  same-event replay, failed HTTP/SD writes, response loss and reconciliation,
  account/book changes, and more than 4 KiB of queued sessions.
- Existing highlight-sync regression suite passed.
- Plugin payload validation passed.

Four independent review axes and their targeted follow-ups are complete.
All substantive findings were resolved. The final X4 Pro build passed without
compiler warnings/errors: static RAM 111,804 / 327,680 bytes; flash
5,483,058 / 6,553,600 bytes. The application image is 5,488,320 bytes, SHA-256
`443332e34f4eb3b868f2ce9e5f3c91e7c89482353566d7636df10ecd2df2d3f9`.

The production HTTP retry-control test passes under AddressSanitizer and
UndefinedBehaviorSanitizer. A scan of changed source and installation artifacts
found no known private device/account values; this is not a guarantee against
all unknown secrets.
Installation was verified on X4 Pro. A retained first session was rejected by
Readwise for a future timestamp caused by the saved loan-clock floor.
Companion highlights.6 changes new session timestamps to fresh RTC UTC; it
leaves the adapter, loan clock and existing records unchanged. Clock-fix host
checks, four review axes and their targeted follow-ups, and the final .6 X4 Pro
build pass. The clock test covers a failed RTC boot probe, unreadable/unset RTC,
time zones, and a future loan-clock floor. The .6 build has no compiler
warnings/errors: static RAM 111,804 / 327,680 bytes and flash
5,483,250 / 6,553,600 bytes. Its application image is 5,488,512 bytes, SHA-256
`9c3e818c975207df1f3d97e047a39d8dc9660ee1431552f3e4bc6fc09ddc0d0d`.
X4 Pro .6 installation and direct Wi-Fi delivery are verified. A new session's
book, UTC interval, active duration, progress and device fields matched the API
record. Its saved receipt matched the exact request hash and API session ID;
the acknowledged queue entry was removed. The user confirmed the duration was
approximately correct. Reconnecting without reading retained the same API ID
and exactly one matching session.
An older retained session also uploaded during sleep after its recorded end
time had passed, matching its original frozen request without rewriting history.

The Books app display, broader offline/restart recovery, stack/heap measurements
and battery impact remain unverified. No synthetic sessions were sent to Readwise.

## Device test

1. Back up the card. Install the X4 Pro companion firmware and run USB setup.
   Confirm the About version and that the setup report links the intended book.
2. Read a linked EPUB, spending at least 10 seconds across ordinary forward
   page turns. Leave the book and connect to Wi-Fi or put the reader to sleep.
3. Confirm one new session in **Readwise Books**, with the correct book, time,
   percentage range, and no social-feed post. Confirm Almanac still gains time.
4. Reconnect without reading more; the Books total must not increase again.
5. Read offline, then reconnect; confirm queued time arrives once. Repeat after
   a normal restart. Allow several connections if multiple sessions are queued.
6. Connect USB and inspect queue totals with the helper's `--status` command.
   A receipt is evidence of API acknowledgment; visible app data is a separate
   check. An uncertain record must not automatically cause a second POST.

Memory estimates: the adapter owns a 12 KiB checked response buffer, bounded
4 KiB record reads, small JSON records and a short-lived TLS client. Parsing uses
a response-field filter. It requires at least 75 KiB free internal heap and a
24 KiB largest block before attempting HTTPS. No buffer or TLS client survives
the call. These gates are not a measured peak budget. Measure internal free
heap, largest block, stack watermark and sleep latency on the device before
claiming long-term stability or battery cost.

The native adapter does not rely on PSRAM. Only X4 Pro is the release target for
this downstream feature; other boards have not been built or tested.
