package nz.teryx.remote;

import android.annotation.SuppressLint;
import android.app.Activity;
import android.app.ActivityManager;
import android.app.admin.DevicePolicyManager;
import android.content.BroadcastReceiver;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.PowerManager;
import android.provider.Settings;
import android.view.View;
import android.view.WindowInsets;
import android.view.WindowInsetsController;
import android.view.WindowManager;
import android.webkit.JavascriptInterface;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

import androidx.webkit.WebViewAssetLoader;

/**
 * Teryx Remote for Android: the pocket OS as a real app.
 *
 * It shows the same page as the iPhone home-screen app (dash/web/remote.html), copied
 * into the APK at build time. The app serves that page to itself on a secure https
 * address (WebViewAssetLoader), so the Gamepad API works with no certificate setup.
 *
 * What the app adds on top of the web page:
 *  - full screen, landscape, screen always on while it's open
 *  - can be the phone's Home app, so it boots straight into the remote
 *  - full kiosk lock if it's made device owner with adb (see android/README.md)
 *  - back button (and a gamepad's B falling through to back) does nothing
 *  - pulling the charger out (taking it out of the glove box) wakes the screen
 *    and tells the page, so it can reconnect to the Teryx
 *
 * The safety rules are not in here. They live in the RC box (teryx/rc_mode.py):
 * if this app dies, its packets stop and the Teryx stops and holds.
 */
public class MainActivity extends Activity {
    private static final String START =
            "https://appassets.androidplatform.net/assets/web/remote.html";

    private WebView web;
    private BroadcastReceiver power;

    @SuppressLint({"SetJavaScriptEnabled", "AddJavascriptInterface"})
    @Override
    protected void onCreate(Bundle saved) {
        super.onCreate(saved);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);

        final WebViewAssetLoader assets = new WebViewAssetLoader.Builder()
                .addPathHandler("/assets/", new WebViewAssetLoader.AssetsPathHandler(this))
                .build();

        web = new WebView(this);
        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setMediaPlaybackRequiresUserGesture(false);   // camera video plays straight away
        s.setTextZoom(100);
        s.setSupportZoom(false);
        // The page is https (served from the APK); the Pi on the hotspot may be plain http.
        s.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);
        web.setOverScrollMode(View.OVER_SCROLL_NEVER);
        web.setBackgroundColor(0xFF070504);
        web.addJavascriptInterface(new Bridge(), "TeryxApp");
        web.setWebViewClient(new WebViewClient() {
            @Override
            public WebResourceResponse shouldInterceptRequest(WebView v, WebResourceRequest r) {
                return assets.shouldInterceptRequest(r.getUrl());
            }
        });
        setContentView(web);
        web.requestFocus();
        if (saved == null) web.loadUrl(START); else web.restoreState(saved);

        // Taken out of the glove box = charger unplugged: wake up and tell the page.
        power = new BroadcastReceiver() {
            @Override
            public void onReceive(Context c, Intent i) {
                wakeScreen();
                web.evaluateJavascript(
                        "window.dispatchEvent(new CustomEvent('teryx-unplugged'))", null);
            }
        };
        registerReceiver(power, new IntentFilter(Intent.ACTION_POWER_DISCONNECTED));
    }

    @Override
    protected void onResume() {
        super.onResume();
        hideBars();
        kioskLock();
        web.onResume();
    }

    @Override
    protected void onPause() {
        web.onPause();
        super.onPause();
    }

    @Override
    protected void onSaveInstanceState(Bundle out) {
        super.onSaveInstanceState(out);
        web.saveState(out);
    }

    @Override
    protected void onDestroy() {
        if (power != null) unregisterReceiver(power);
        web.destroy();
        super.onDestroy();
    }

    @Override
    public void onWindowFocusChanged(boolean focus) {
        super.onWindowFocusChanged(focus);
        if (focus) hideBars();
    }

    /** Back does nothing: it's a remote, not a browser. A gamepad's B can fall through to back. */
    @SuppressWarnings("deprecation")
    @Override
    public void onBackPressed() { }

    private void hideBars() {
        if (Build.VERSION.SDK_INT >= 30) {
            WindowInsetsController c = getWindow().getInsetsController();
            if (c != null) {
                c.hide(WindowInsets.Type.systemBars());
                c.setSystemBarsBehavior(WindowInsetsController.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE);
            }
        } else {
            getWindow().getDecorView().setSystemUiVisibility(
                    View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY | View.SYSTEM_UI_FLAG_FULLSCREEN
                            | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION | View.SYSTEM_UI_FLAG_LAYOUT_STABLE
                            | View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION | View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN);
        }
    }

    /** Full kiosk lock, only when the app has been made device owner (adb). Otherwise no-op. */
    private void kioskLock() {
        DevicePolicyManager dpm = (DevicePolicyManager) getSystemService(DEVICE_POLICY_SERVICE);
        if (dpm == null || !dpm.isDeviceOwnerApp(getPackageName())) return;
        dpm.setLockTaskPackages(new ComponentName(this, AdminReceiver.class),
                new String[]{getPackageName(), "com.android.settings"});
        ActivityManager am = (ActivityManager) getSystemService(ACTIVITY_SERVICE);
        if (am != null && am.getLockTaskModeState() == ActivityManager.LOCK_TASK_MODE_NONE) {
            startLockTask();
        }
    }

    @SuppressWarnings("deprecation")
    private void wakeScreen() {
        PowerManager pm = (PowerManager) getSystemService(POWER_SERVICE);
        if (pm == null || pm.isInteractive()) return;
        PowerManager.WakeLock wl = pm.newWakeLock(
                PowerManager.SCREEN_BRIGHT_WAKE_LOCK | PowerManager.ACQUIRE_CAUSES_WAKEUP,
                "teryx:unplugged");
        wl.acquire(5000);
    }

    /** What the page can ask the app for, as window.TeryxApp. */
    private class Bridge {
        @JavascriptInterface
        public String version() {
            try {
                return getPackageManager().getPackageInfo(getPackageName(), 0).versionName;
            } catch (Exception e) {
                return "?";
            }
        }

        @JavascriptInterface
        public boolean kiosk() {
            DevicePolicyManager dpm = (DevicePolicyManager) getSystemService(DEVICE_POLICY_SERVICE);
            return dpm != null && dpm.isDeviceOwnerApp(getPackageName());
        }

        /** Leave the remote for the phone's settings (the page asks for the PIN first). */
        @JavascriptInterface
        public void phoneSettings() {
            runOnUiThread(() -> {
                try { stopLockTask(); } catch (Exception ignored) { }
                startActivity(new Intent(Settings.ACTION_SETTINGS).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK));
            });
        }

        /** Open the Wi-Fi settings, to join the Teryx's hotspot the first time. */
        @JavascriptInterface
        public void wifiSettings() {
            runOnUiThread(() -> startActivity(
                    new Intent(Settings.ACTION_WIFI_SETTINGS).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)));
        }
    }
}
