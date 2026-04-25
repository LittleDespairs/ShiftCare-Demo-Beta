package com.scheduleapp.tablet;

import android.annotation.SuppressLint;
import android.app.Activity;
import android.app.DownloadManager;
import android.content.res.AssetManager;
import android.graphics.Color;
import android.net.Uri;
import android.os.Bundle;
import android.os.Environment;
import android.os.Handler;
import android.os.Looper;
import android.view.Gravity;
import android.view.ViewGroup;
import android.webkit.DownloadListener;
import android.webkit.JavascriptInterface;
import android.webkit.WebChromeClient;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Toast;
import android.widget.FrameLayout;
import android.widget.ProgressBar;
import android.widget.TextView;

import com.chaquo.python.PyObject;
import com.chaquo.python.Python;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;

public class MainActivity extends Activity {
    private final Handler mainHandler = new Handler(Looper.getMainLooper());
    private FrameLayout root;
    private FrameLayout loadingPanel;
    private WebView webView;
    private TextView statusText;
    private ProgressBar progressBar;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        buildLayout();
        startBackendAndLoad();
    }

    @SuppressLint("SetJavaScriptEnabled")
    private void buildLayout() {
        root = new FrameLayout(this);
        root.setBackgroundColor(Color.rgb(244, 247, 251));

        webView = new WebView(this);
        webView.setVisibility(WebView.INVISIBLE);
        webView.setWebViewClient(new WebViewClient());
        webView.setWebChromeClient(new WebChromeClient());
        webView.setDownloadListener(createDownloadListener());
        webView.addJavascriptInterface(new ScheduleAndroidBridge(), "ScheduleAndroid");

        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setDatabaseEnabled(true);
        settings.setLoadWithOverviewMode(true);
        settings.setUseWideViewPort(true);
        settings.setBuiltInZoomControls(false);
        settings.setDisplayZoomControls(false);
        settings.setAllowFileAccess(false);
        settings.setAllowContentAccess(false);

        root.addView(webView, new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.MATCH_PARENT
        ));

        loadingPanel = new FrameLayout(this);
        loadingPanel.setPadding(32, 32, 32, 32);

        progressBar = new ProgressBar(this);
        FrameLayout.LayoutParams progressParams = new FrameLayout.LayoutParams(96, 96);
        progressParams.gravity = Gravity.CENTER;
        progressParams.bottomMargin = 72;
        loadingPanel.addView(progressBar, progressParams);

        statusText = new TextView(this);
        statusText.setText("Starting Schedule App...");
        statusText.setTextColor(Color.rgb(30, 41, 59));
        statusText.setTextSize(18);
        statusText.setGravity(Gravity.CENTER);
        FrameLayout.LayoutParams textParams = new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT
        );
        textParams.gravity = Gravity.CENTER;
        textParams.topMargin = 128;
        loadingPanel.addView(statusText, textParams);

        root.addView(loadingPanel, new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.MATCH_PARENT
        ));

        setContentView(root);
    }

    private DownloadListener createDownloadListener() {
        return (url, userAgent, contentDisposition, mimetype, contentLength) -> {
            try {
                String filename = "schedule_export.xlsx";
                int filenameIndex = contentDisposition == null ? -1 : contentDisposition.indexOf("filename=");
                if (filenameIndex >= 0) {
                    filename = contentDisposition.substring(filenameIndex + "filename=".length())
                            .replace("\"", "")
                            .trim();
                }

                enqueueDownload(url, filename, mimetype, userAgent);
                Toast.makeText(this, "Export saved to Downloads", Toast.LENGTH_LONG).show();
            } catch (Exception error) {
                Toast.makeText(this, "Export failed: " + error.getMessage(), Toast.LENGTH_LONG).show();
            }
        };
    }

    private class ScheduleAndroidBridge {
        @JavascriptInterface
        public void downloadFile(String url, String filename, String mimeType) {
            mainHandler.post(() -> {
                try {
                    enqueueDownload(url, filename, mimeType, null);
                    Toast.makeText(MainActivity.this, "Export saved to Downloads", Toast.LENGTH_LONG).show();
                } catch (Exception error) {
                    Toast.makeText(MainActivity.this, "Export failed: " + error.getMessage(), Toast.LENGTH_LONG).show();
                }
            });
        }
    }

    private void enqueueDownload(String url, String filename, String mimeType, String userAgent) {
        DownloadManager.Request request = new DownloadManager.Request(Uri.parse(url));
        request.setMimeType(mimeType);
        if (userAgent != null) {
            request.addRequestHeader("User-Agent", userAgent);
        }
        request.setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED);
        request.setDestinationInExternalPublicDir(Environment.DIRECTORY_DOWNLOADS, filename);

        DownloadManager downloadManager = (DownloadManager) getSystemService(DOWNLOAD_SERVICE);
        if (downloadManager != null) {
            downloadManager.enqueue(request);
        }
    }

    private void startBackendAndLoad() {
        Thread thread = new Thread(() -> {
            try {
                File backendDir = new File(getFilesDir(), "schedule_app_backend");
                copyAssetFolder("schedule_app_backend", backendDir);
                Python py = Python.getInstance();
                PyObject bridge = py.getModule("app_bridge");
                String url = bridge.callAttr("start_server", backendDir.getAbsolutePath()).toString();
                mainHandler.post(() -> {
                    webView.loadUrl(url);
                    webView.setVisibility(WebView.VISIBLE);
                    loadingPanel.setVisibility(android.view.View.GONE);
                });
            } catch (Exception error) {
                mainHandler.post(() -> {
                    statusText.setText("Failed to start Schedule App:\n" + error.getMessage());
                    progressBar.setVisibility(android.view.View.GONE);
                });
            }
        });
        thread.setDaemon(true);
        thread.start();
    }

    private void copyAssetFolder(String assetPath, File targetDir) throws IOException {
        AssetManager assetManager = getAssets();
        String[] children = assetManager.list(assetPath);

        if (children == null || children.length == 0) {
            copyAssetFile(assetPath, targetDir);
            return;
        }

        if (!targetDir.exists() && !targetDir.mkdirs()) {
            throw new IOException("Cannot create directory: " + targetDir.getAbsolutePath());
        }

        for (String child : children) {
            copyAssetFolder(assetPath + "/" + child, new File(targetDir, child));
        }
    }

    private void copyAssetFile(String assetPath, File targetFile) throws IOException {
        File parent = targetFile.getParentFile();
        if (parent != null && !parent.exists() && !parent.mkdirs()) {
            throw new IOException("Cannot create directory: " + parent.getAbsolutePath());
        }

        try (InputStream input = getAssets().open(assetPath);
             OutputStream output = new FileOutputStream(targetFile, false)) {
            byte[] buffer = new byte[8192];
            int length;
            while ((length = input.read(buffer)) > 0) {
                output.write(buffer, 0, length);
            }
        }
    }

    @Override
    public void onBackPressed() {
        if (webView != null && webView.canGoBack()) {
            webView.goBack();
        } else {
            super.onBackPressed();
        }
    }
}
