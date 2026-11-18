package nz.teryx.remote;

import android.app.admin.DeviceAdminReceiver;

/** Lets the app be the phone's device owner (set with adb), which allows a full kiosk lock. */
public class AdminReceiver extends DeviceAdminReceiver {}
