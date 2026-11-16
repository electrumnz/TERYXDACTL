#!/bin/bash
# Opens the dash full screen. Waits for the dash server first.
# --use-fake-ui-for-media-stream lets the reverse camera open without a permission pop-up.
URL="${TERYX_DASH_URL:-http://localhost:8080/}"
for _ in $(seq 1 60); do curl -sf "$URL" >/dev/null && break; sleep 1; done
BROWSER=$(command -v chromium || command -v chromium-browser)
exec "$BROWSER" --kiosk "$URL" \
  --noerrdialogs --disable-infobars --no-first-run --disable-translate \
  --disable-pinch --overscroll-history-navigation=0 --disable-features=TranslateUI,OverscrollHistoryNavigation \
  --use-fake-ui-for-media-stream --autoplay-policy=no-user-gesture-required \
  --check-for-update-interval=31536000 --password-store=basic
