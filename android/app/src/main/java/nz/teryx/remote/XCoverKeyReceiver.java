package nz.teryx.remote;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;

/**
 * Samsung XCover phones (XCover 5 and others) have a programmable side key. When the
 * user picks this app under Settings > Advanced features > XCover key > "Control XCover
 * key with app", Samsung sends every press here (Knox "unmanaged key mapping"; no Knox
 * licence mentioned for this). We use it as a hardware STOP: press it and the remote
 * e-stops, which stops the Teryx and holds it on the brake.
 */
public class XCoverKeyReceiver extends BroadcastReceiver {
    static final String ACTION = "com.samsung.android.knox.intent.action.HARD_KEY_REPORT";
    static final String EXTRA_CODE = "com.samsung.android.knox.intent.extra.KEY_CODE";
    static final String EXTRA_TYPE = "com.samsung.android.knox.intent.extra.KEY_REPORT_TYPE";
    static final int KEY_XCOVER = 1015;   // KEYCODE_PTT, the XCover key
    static final int KEY_TOP = 1079;      // KEYCODE_EMERGENCY, the top key on XCover Pro models
    static final int DOWN = 1;

    @Override
    public void onReceive(Context c, Intent i) {
        if (!ACTION.equals(i.getAction())) return;
        int code = i.getIntExtra(EXTRA_CODE, 0);
        int type = i.getIntExtra(EXTRA_TYPE, 0);
        if ((code == KEY_XCOVER || code == KEY_TOP) && type == DOWN) MainActivity.hardStop();
    }
}
