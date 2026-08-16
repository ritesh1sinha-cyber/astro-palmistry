package com.graharekha.app;

import android.Manifest;
import android.app.DownloadManager;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.net.Uri;
import android.os.Bundle;
import android.os.Environment;
import android.os.Message;
import android.provider.MediaStore;
import android.text.TextUtils;
import android.view.View;
import android.view.ViewGroup;
import android.webkit.CookieManager;
import android.webkit.PermissionRequest;
import android.webkit.URLUtil;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.FrameLayout;
import android.widget.Toast;

import androidx.activity.OnBackPressedCallback;
import androidx.activity.result.ActivityResult;
import androidx.activity.result.ActivityResultLauncher;
import androidx.activity.result.contract.ActivityResultContracts;
import androidx.annotation.NonNull;
import androidx.annotation.Nullable;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.content.ContextCompat;
import androidx.core.content.FileProvider;

import java.io.File;
import java.net.URISyntaxException;
import java.util.Arrays;
import java.util.List;

/**
 * A WebView shell over the GrahaRekha site.
 *
 * The page is not an ordinary document: it photographs palms through getUserMedia
 * and a file input, it pays through Razorpay which hands off to UPI apps, it opens
 * reports in new windows, and it serves PDFs. A default WebView breaks every one of
 * those, so most of this class is the four hand-offs that make them work.
 */
public class MainActivity extends AppCompatActivity {

    /** Links that belong to another app on the phone rather than to this one. */
    private static final List<String> EXTERNAL_HOSTS =
            Arrays.asList("wa.me", "api.whatsapp.com", "chat.whatsapp.com");

    private FrameLayout popupHost;
    private WebView web;

    @Nullable private ValueCallback<Uri[]> fileCallback;
    @Nullable private Uri cameraOutput;
    @Nullable private PermissionRequest pendingCameraRequest;

    private final ActivityResultLauncher<Intent> filePicker = registerForActivityResult(
            new ActivityResultContracts.StartActivityForResult(), this::onFileChosen);

    private final ActivityResultLauncher<String> cameraPermission = registerForActivityResult(
            new ActivityResultContracts.RequestPermission(), this::onCameraPermissionResult);

    @Override
    protected void onCreate(@Nullable Bundle state) {
        super.onCreate(state);
        setContentView(R.layout.activity_main);
        popupHost = findViewById(R.id.popup_host);
        web = findViewById(R.id.web);

        WebView.setWebContentsDebuggingEnabled(BuildConfig.DEBUG);
        configure(web);
        web.setWebViewClient(new ShellWebViewClient());
        web.setWebChromeClient(new ShellChromeClient());

        getOnBackPressedDispatcher().addCallback(this, new OnBackPressedCallback(true) {
            @Override
            public void handleOnBackPressed() {
                if (popupHost.getVisibility() == View.VISIBLE) {
                    closePopup();
                } else if (web.canGoBack()) {
                    web.goBack();
                } else {
                    finish();
                }
            }
        });

        if (state != null) {
            web.restoreState(state);
        } else {
            web.loadUrl(BuildConfig.BASE_URL);
        }

        // Asked once, up front: the palm reading is the reason the app exists, and
        // the camera intent below is unusable while the permission is outstanding
        // because declaring CAMERA makes the system require it.
        if (!hasCamera()) {
            cameraPermission.launch(Manifest.permission.CAMERA);
        }
    }

    // ---------------------------------------------------------------- settings

    private void configure(WebView view) {
        WebSettings s = view.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setDatabaseEnabled(true);
        s.setUseWideViewPort(true);
        s.setLoadWithOverviewMode(true);
        s.setSupportZoom(false);
        s.setBuiltInZoomControls(false);
        s.setDisplayZoomControls(false);
        // Palm capture starts on a button press inside the page, and the WebView
        // would otherwise demand a second gesture of its own before the stream runs.
        s.setMediaPlaybackRequiresUserGesture(false);
        s.setJavaScriptCanOpenWindowsAutomatically(true);
        s.setSupportMultipleWindows(true);
        s.setAllowFileAccess(false);
        s.setAllowContentAccess(true);
        s.setMixedContentMode(BuildConfig.ALLOW_PLAIN_HTTP
                ? WebSettings.MIXED_CONTENT_COMPATIBILITY_MODE
                : WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        s.setUserAgentString(browserUserAgent(s.getUserAgentString()));

        CookieManager cookies = CookieManager.getInstance();
        cookies.setAcceptCookie(true);
        // Google's sign-in iframe and Razorpay's checkout are both third parties
        // setting cookies on themselves; without this they cannot keep a session.
        cookies.setAcceptThirdPartyCookies(view, true);

        view.setDownloadListener((url, userAgent, disposition, mime, length) ->
                download(url, disposition, mime));
    }

    /**
     * The WebView advertises itself with a {@code wv} token, and Google Sign-In
     * refuses to render for any user agent carrying it. Presenting the underlying
     * Chrome instead keeps the sign-in button alive; the promocode login does not
     * depend on this.
     */
    private static String browserUserAgent(String original) {
        if (TextUtils.isEmpty(original)) {
            return original;
        }
        return original
                .replace("; wv)", ")")
                .replaceAll("Version/\\d+(\\.\\d+)* ", "");
    }

    // ------------------------------------------------------------ navigation

    private class ShellWebViewClient extends WebViewClient {

        @Override
        public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
            Uri uri = request.getUrl();
            String scheme = uri.getScheme();
            if (scheme == null) {
                return false;
            }
            boolean http = "http".equals(scheme) || "https".equals(scheme);
            if (http && !EXTERNAL_HOSTS.contains(String.valueOf(uri.getHost()))) {
                return false;
            }
            return openExternally(view, uri.toString());
        }

        @Override
        public void onReceivedError(WebView view, WebResourceRequest request,
                                    WebResourceError error) {
            if (request.isForMainFrame()) {
                view.loadDataWithBaseURL(null, offlinePage(), "text/html", "utf-8", null);
            }
        }
    }

    /**
     * Sends a link to whichever app owns it. Razorpay completes UPI payments by
     * navigating to {@code upi:}, {@code intent:} and vendor schemes such as
     * {@code phonepe:}; inside a WebView those come back as ERR_UNKNOWN_URL_SCHEME
     * and the payment dead-ends with the customer's money uncommitted.
     */
    private boolean openExternally(WebView view, String url) {
        Intent intent = null;
        String fallback = null;
        if (url.startsWith("intent:")) {
            try {
                intent = Intent.parseUri(url, Intent.URI_INTENT_SCHEME);
                fallback = intent.getStringExtra("browser_fallback_url");
                // The URL came from a web page, so it is not allowed to name a
                // component or a selector and reach into another app's internals.
                intent.setComponent(null);
                intent.setSelector(null);
            } catch (URISyntaxException e) {
                intent = null;
            }
        } else {
            intent = new Intent(Intent.ACTION_VIEW, Uri.parse(url));
        }
        if (intent != null) {
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            try {
                startActivity(intent);
                return true;
            } catch (Exception ignored) {
                // No app claims the scheme; fall through to the page's own fallback.
            }
        }
        if (!TextUtils.isEmpty(fallback)) {
            view.loadUrl(fallback);
            return true;
        }
        toast(getString(R.string.no_app_for_link));
        return true;
    }

    private String offlinePage() {
        return "<!doctype html><html><head><meta name='viewport' "
                + "content='width=device-width,initial-scale=1'><style>"
                + "body{margin:0;min-height:100vh;display:flex;align-items:center;"
                + "justify-content:center;background:#f7f5f0;color:#16181d;"
                + "font-family:system-ui,-apple-system,sans-serif;text-align:center}"
                + "div{padding:32px;max-width:22rem}h1{font-size:1.25rem;margin:0 0 10px}"
                + "p{color:#6a7080;line-height:1.6;margin:0 0 22px}"
                + "a{display:inline-block;padding:12px 26px;border-radius:999px;"
                + "background:#c9a227;color:#fff;text-decoration:none;font-weight:600}"
                + "</style></head><body><div><h1>No connection</h1>"
                + "<p>GrahaRekha could not be reached. Check your network and try again.</p>"
                + "<a href='" + BuildConfig.BASE_URL + "'>Try again</a>"
                + "</div></body></html>";
    }

    // ----------------------------------------------------------------- popups

    private class ShellChromeClient extends WebChromeClient {

        @Override
        public boolean onCreateWindow(WebView view, boolean isDialog,
                                      boolean isUserGesture, Message resultMsg) {
            WebView popup = new WebView(MainActivity.this);
            configure(popup);
            popup.setWebViewClient(new ShellWebViewClient());
            popup.setWebChromeClient(new WebChromeClient() {
                @Override
                public void onCloseWindow(WebView window) {
                    closePopup();
                }
            });
            popup.setLayoutParams(new FrameLayout.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT,
                    ViewGroup.LayoutParams.MATCH_PARENT));
            closePopup();
            popupHost.addView(popup);
            popupHost.setVisibility(View.VISIBLE);
            ((WebView.WebViewTransport) resultMsg.obj).setWebView(popup);
            resultMsg.sendToTarget();
            return true;
        }

        @Override
        public void onCloseWindow(WebView window) {
            closePopup();
        }

        @Override
        public void onPermissionRequest(PermissionRequest request) {
            boolean wantsCamera = false;
            for (String resource : request.getResources()) {
                if (PermissionRequest.RESOURCE_VIDEO_CAPTURE.equals(resource)) {
                    wantsCamera = true;
                }
            }
            if (!wantsCamera) {
                request.deny();
                return;
            }
            if (hasCamera()) {
                request.grant(request.getResources());
                return;
            }
            // The page asked for the camera before Android granted it to us. Hold
            // the request and answer it once the user has decided.
            pendingCameraRequest = request;
            cameraPermission.launch(Manifest.permission.CAMERA);
        }

        @Override
        public boolean onShowFileChooser(WebView view,
                                         ValueCallback<Uri[]> callback,
                                         FileChooserParams params) {
            if (fileCallback != null) {
                fileCallback.onReceiveValue(null);
            }
            fileCallback = callback;
            try {
                filePicker.launch(chooserFor(params));
                return true;
            } catch (Exception e) {
                fileCallback = null;
                return false;
            }
        }
    }

    private void closePopup() {
        for (int i = popupHost.getChildCount() - 1; i >= 0; i--) {
            View child = popupHost.getChildAt(i);
            popupHost.removeViewAt(i);
            if (child instanceof WebView) {
                ((WebView) child).destroy();
            }
        }
        popupHost.setVisibility(View.GONE);
    }

    // ------------------------------------------------------------ palm photos

    private Intent chooserFor(WebChromeClient.FileChooserParams params) {
        Intent pick = params.createIntent();
        Intent chooser = new Intent(Intent.ACTION_CHOOSER);
        chooser.putExtra(Intent.EXTRA_INTENT, pick);
        chooser.putExtra(Intent.EXTRA_TITLE, getString(R.string.pick_palm_photo));
        Intent capture = captureIntent();
        if (capture != null) {
            chooser.putExtra(Intent.EXTRA_INITIAL_INTENTS, new Intent[]{capture});
        }
        return chooser;
    }

    /** A camera option alongside the gallery, so a palm can be shot on the spot. */
    @Nullable
    private Intent captureIntent() {
        if (!hasCamera()) {
            return null;
        }
        try {
            File dir = new File(getCacheDir(), "captures");
            if (!dir.exists() && !dir.mkdirs()) {
                return null;
            }
            File target = new File(dir, "palm-" + System.currentTimeMillis() + ".jpg");
            cameraOutput = FileProvider.getUriForFile(
                    this, getPackageName() + ".fileprovider", target);
            Intent capture = new Intent(MediaStore.ACTION_IMAGE_CAPTURE);
            capture.putExtra(MediaStore.EXTRA_OUTPUT, cameraOutput);
            capture.addFlags(Intent.FLAG_GRANT_WRITE_URI_PERMISSION);
            return capture;
        } catch (Exception e) {
            cameraOutput = null;
            return null;
        }
    }

    private void onFileChosen(ActivityResult result) {
        if (fileCallback == null) {
            return;
        }
        Uri[] chosen = null;
        Intent data = result.getData();
        if (result.getResultCode() == RESULT_OK) {
            if (data == null) {
                // The camera app writes straight to the file we handed it and
                // returns nothing, so silence here means the capture succeeded.
                chosen = cameraOutput == null ? null : new Uri[]{cameraOutput};
            } else if (data.getClipData() != null) {
                int count = data.getClipData().getItemCount();
                chosen = new Uri[count];
                for (int i = 0; i < count; i++) {
                    chosen[i] = data.getClipData().getItemAt(i).getUri();
                }
            } else if (data.getData() != null) {
                chosen = new Uri[]{data.getData()};
            } else if (cameraOutput != null) {
                chosen = new Uri[]{cameraOutput};
            }
        }
        fileCallback.onReceiveValue(chosen);
        fileCallback = null;
        cameraOutput = null;
    }

    private void onCameraPermissionResult(boolean granted) {
        PermissionRequest request = pendingCameraRequest;
        pendingCameraRequest = null;
        if (request != null) {
            if (granted) {
                request.grant(request.getResources());
            } else {
                request.deny();
                toast(getString(R.string.camera_needed));
            }
        }
    }

    private boolean hasCamera() {
        return ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA)
                == PackageManager.PERMISSION_GRANTED;
    }

    // -------------------------------------------------------------- downloads

    /** Report PDFs are behind a session, so the cookie has to travel with them. */
    private void download(String url, String disposition, String mime) {
        if (url == null || url.startsWith("blob:") || url.startsWith("data:")) {
            toast(getString(R.string.download_failed));
            return;
        }
        try {
            String name = URLUtil.guessFileName(url, disposition, mime);
            DownloadManager.Request request = new DownloadManager.Request(Uri.parse(url));
            request.setMimeType(mime);
            request.addRequestHeader("Cookie", CookieManager.getInstance().getCookie(url));
            request.addRequestHeader("User-Agent", web.getSettings().getUserAgentString());
            request.setTitle(name);
            request.setNotificationVisibility(
                    DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED);
            request.setDestinationInExternalPublicDir(Environment.DIRECTORY_DOWNLOADS, name);
            DownloadManager manager = getSystemService(DownloadManager.class);
            if (manager == null) {
                toast(getString(R.string.download_failed));
                return;
            }
            manager.enqueue(request);
            toast(getString(R.string.download_started));
        } catch (Exception e) {
            toast(getString(R.string.download_failed));
        }
    }

    // ------------------------------------------------------------- lifecycle

    @Override
    protected void onSaveInstanceState(@NonNull Bundle state) {
        super.onSaveInstanceState(state);
        web.saveState(state);
    }

    @Override
    protected void onPause() {
        super.onPause();
        // Persist the login cookie now, so being killed in the background does not
        // sign the reader out mid-reading.
        CookieManager.getInstance().flush();
    }

    @Override
    protected void onDestroy() {
        closePopup();
        super.onDestroy();
    }

    private void toast(String message) {
        Toast.makeText(this, message, Toast.LENGTH_SHORT).show();
    }
}
