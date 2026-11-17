package local.sapphire.memoryextension;

import android.app.Activity;
import android.app.AlertDialog;
import android.os.Bundle;
import android.view.View;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.RadioButton;
import android.widget.RadioGroup;
import android.widget.ScrollView;
import android.widget.TextView;
import org.json.JSONObject;
import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.util.Locale;

public final class MainActivity extends Activity {
    private TextView status;
    private RadioGroup choices;
    private Button save;
    private Button reboot;
    private boolean connected;
    private final String control = "/system/bin/sh /data/adb/sapphire-extm/control.sh ";

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        setTitle("Memory extension");
        ScrollView scroll = new ScrollView(this);
        LinearLayout layout = new LinearLayout(this);
        layout.setOrientation(LinearLayout.VERTICAL);
        int pad = (int)(24 * getResources().getDisplayMetrics().density);
        layout.setPadding(pad, pad, pad, pad);
        layout.setFocusableInTouchMode(true);
        layout.requestFocus();
        scroll.setOnApplyWindowInsetsListener((view, insets) -> {
            if (android.os.Build.VERSION.SDK_INT >= 30) {
                android.graphics.Insets bars = insets.getInsets(android.view.WindowInsets.Type.systemBars() | android.view.WindowInsets.Type.displayCutout());
                layout.setPadding(pad + bars.left, pad, pad + bars.right, pad + bars.bottom);
            }
            return insets;
        });
        scroll.addView(layout);
        TextView intro = new TextView(this);
        intro.setTextSize(17);
        intro.setText("Use encrypted storage to back compressed RAM. This can keep more idle data available; it does not add physical RAM.");
        layout.addView(intro);
        status = new TextView(this);
        status.setTextSize(16);
        status.setPadding(0, pad, 0, pad);
        status.setText("Tap Refresh to read the live configuration. Root permission is required.");
        layout.addView(status);
        choices = new RadioGroup(this);
        String[] labels = {"Off · ROM default", "4 GiB extension · 6 GiB compressed RAM", "8 GiB extension · 8 GiB compressed RAM"};
        int[] values = {0,4,8};
        for (int i=0; i<values.length; i++) {
            RadioButton button = new RadioButton(this);
            button.setId(100 + values[i]);
            button.setText(labels[i]);
            choices.addView(button);
        }
        layout.addView(choices);
        Button refresh = new Button(this);
        refresh.setText("Refresh / allow root");
        refresh.setOnClickListener(v -> load());
        layout.addView(refresh);
        save = new Button(this);
        save.setText("Save for next restart");
        save.setEnabled(false);
        save.setOnClickListener(v -> {
            int value = choices.getCheckedRadioButtonId() - 100;
            if (!connected || (value!=0 && value!=4 && value!=8)) return;
            runRoot("set " + value, text -> { status.setText(text); load(); });
        });
        layout.addView(save);
        reboot = new Button(this);
        reboot.setText("Restart phone…");
        reboot.setEnabled(false);
        reboot.setOnClickListener(v -> new AlertDialog.Builder(this)
            .setTitle("Restart to apply?")
            .setMessage("Save any open work first. The phone will restart to apply the selected memory configuration.")
            .setNegativeButton("Cancel", null)
            .setPositiveButton("Restart", (dialog, which) -> runRootCommand("/system/bin/reboot", text -> status.setText(text)))
            .show());
        layout.addView(reboot);
        TextView note = new TextView(this);
        note.setPadding(0,pad,0,0);
        note.setText("Storage-backed pages are slower than RAM. Changes apply after a restart. Writeback is limited to 1 GiB per day and runs only under memory pressure while the screen is asleep.");
        layout.addView(note);
        setContentView(scroll);
        scroll.requestApplyInsets();
    }
    private interface Result { void accept(String text); }
    private void runRoot(String args, Result result) { runRootCommand(control + args, result); }
    private void runRootCommand(String command, Result result) {
        new Thread(() -> {
            try {
                // Commands are fixed by this UI. Intent extras are never interpreted.
                Process p = new ProcessBuilder("/product/bin/su", "-c", command).start();
                p.getOutputStream().close();
                String stdout = read(p.getInputStream());
                String stderr = read(p.getErrorStream());
                int code = p.waitFor();
                if (code!=0) throw new Exception(stderr.isEmpty() ? "Root permission was denied or the module is unavailable." : stderr);
                runOnUiThread(() -> result.accept(stdout.trim()));
            } catch (Exception e) {
                runOnUiThread(() -> {
                    connected=false; save.setEnabled(false); reboot.setEnabled(false);
                    status.setText("Unable to read configuration: " + e.getMessage());
                });
            }
        }, "memory-extension-control").start();
    }
    private static String read(InputStream stream) throws Exception {
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        byte[] buf = new byte[4096]; int n;
        while ((n=stream.read(buf))!=-1) out.write(buf,0,n);
        return new String(out.toByteArray(), "UTF-8");
    }
    private void load() {
        status.setText("Reading configuration…");
        runRoot("status", text -> {
            try {
                JSONObject o = new JSONObject(text);
                int desired=o.getInt("configured_gib"), active=o.getInt("effective_gib");
                choices.check(100 + desired);
                connected=true; save.setEnabled(true); reboot.setEnabled(desired!=active);
                status.setText(String.format(Locale.US,
                    "Physical RAM: %.1f GiB\nCompressed RAM: %.1f GiB\nMemory extension active: %s\nSaved selection: %s%s\nCompression: %s",
                    o.getDouble("physical_bytes")/1073741824.0,
                    o.getDouble("zram_bytes")/1073741824.0,
                    active==0 ? "Off" : active+" GiB",
                    desired==0 ? "Off" : desired+" GiB",
                    desired!=active ? " · restart required" : "",
                    o.getString("algorithm")));
            } catch (Exception e) { status.setText("Invalid status response: " + e.getMessage()); }
        });
    }
}
