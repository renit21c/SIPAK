package com.sipak.app;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.ActivityNotFoundException;
import android.content.ClipData;
import android.content.Intent;
import android.graphics.Color;
import android.net.Uri;
import android.net.http.SslError;
import android.os.Build;
import android.os.Bundle;
import android.os.Message;
import android.view.Gravity;
import android.view.View;
import android.view.WindowInsets;
import android.webkit.CookieManager;
import android.webkit.SslErrorHandler;
import android.webkit.URLUtil;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;

import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.ArrayList;
import java.util.Locale;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public final class MainActivity extends Activity {
    private static final String HOME = "https://sipak.up.railway.app/";
    private static final int CHOOSE_FILE = 40, SAVE_DOCUMENT = 41;
    private WebView web;
    private LinearLayout offline;
    private ValueCallback<Uri[]> fileCallback;
    private String pendingDownload;
    private boolean navigationFailed;
    private final ExecutorService downloads = Executors.newSingleThreadExecutor();

    private static boolean trusted(Uri uri) {
        return "https".equalsIgnoreCase(uri.getScheme())
            && "sipak.up.railway.app".equalsIgnoreCase(uri.getHost())
            && (uri.getPort() == -1 || uri.getPort() == 443);
    }

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        FrameLayout root = new FrameLayout(this);
        root.setBackgroundColor(Color.rgb(37,40,95));
        setContentView(root);
        if (Build.VERSION.SDK_INT >= 30) {
            getWindow().setDecorFitsSystemWindows(false);
            root.setOnApplyWindowInsetsListener((view, insets) -> {
                android.graphics.Insets bars = insets.getInsets(WindowInsets.Type.systemBars() | WindowInsets.Type.displayCutout());
                android.graphics.Insets keyboard = insets.getInsets(WindowInsets.Type.ime());
                view.setPadding(bars.left,bars.top,bars.right,Math.max(bars.bottom,keyboard.bottom));
                return insets;
            });
        }
        web = new WebView(this);
        root.addView(web,new FrameLayout.LayoutParams(-1,-1));
        web.setBackgroundColor(Color.rgb(233,237,247));
        WebView.setWebContentsDebuggingEnabled(BuildConfig.DEBUG);
        WebSettings settings = web.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setAllowFileAccess(false);
        settings.setAllowContentAccess(true);
        settings.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        settings.setSafeBrowsingEnabled(true);
        settings.setMediaPlaybackRequiresUserGesture(false);
        settings.setSupportMultipleWindows(true);
        CookieManager.getInstance().setAcceptCookie(true);
        CookieManager.getInstance().setAcceptThirdPartyCookies(web,false);
        web.setWebViewClient(new WebViewClient() {
            @Override public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                return request.isForMainFrame() && navigate(request.getUrl());
            }
            @Override public void onPageStarted(WebView view,String url,android.graphics.Bitmap icon) { navigationFailed=false; }
            @Override public void onPageCommitVisible(WebView view,String url) {
                if (trusted(Uri.parse(url)) && !navigationFailed) offline.setVisibility(View.GONE);
            }
            @Override public void onReceivedError(WebView view,WebResourceRequest request,WebResourceError error) {
                if (request.isForMainFrame()) showOffline();
            }
            @Override public void onReceivedHttpError(WebView view,WebResourceRequest request,WebResourceResponse response) {
                if (request.isForMainFrame() && response.getStatusCode() >= 500) showOffline();
            }
            @Override public void onReceivedSslError(WebView view,SslErrorHandler handler,SslError error) {
                handler.cancel(); showOffline();
            }
        });
        web.setWebChromeClient(new WebChromeClient() {
            @Override public boolean onShowFileChooser(WebView view,ValueCallback<Uri[]> callback,FileChooserParams parameters) {
                if (fileCallback != null) fileCallback.onReceiveValue(null);
                fileCallback = callback;
                Intent intent = parameters.createIntent();
                intent.setAction(Intent.ACTION_OPEN_DOCUMENT);
                intent.addCategory(Intent.CATEGORY_OPENABLE);
                intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
                try { startActivityForResult(intent,CHOOSE_FILE); }
                catch (ActivityNotFoundException error) { fileCallback.onReceiveValue(null); fileCallback=null; message("Pemilih file tidak tersedia."); }
                return true;
            }
            @Override public boolean onCreateWindow(WebView view,boolean dialog,boolean gesture,Message result) {
                if (!gesture) return false;
                WebView popup = new WebView(MainActivity.this);
                popup.setWebViewClient(new WebViewClient() {
                    @Override public boolean shouldOverrideUrlLoading(WebView child,WebResourceRequest request) {
                        Uri uri=request.getUrl();
                        if (!navigate(uri) && trusted(uri)) web.loadUrl(uri.toString());
                        child.destroy();return true;
                    }
                });
                ((WebView.WebViewTransport)result.obj).setWebView(popup);
                result.sendToTarget();return true;
            }
        });
        web.setDownloadListener((url,agent,disposition,mime,length) -> requestDownload(url,URLUtil.guessFileName(url,disposition,mime)));
        offline = new LinearLayout(this);
        offline.setOrientation(LinearLayout.VERTICAL);
        offline.setGravity(Gravity.CENTER);
        offline.setPadding(32,32,32,32);
        offline.setBackgroundColor(Color.rgb(233,237,247));
        TextView title = new TextView(this);
        title.setText(R.string.offline_title);title.setTextSize(23);title.setTextColor(Color.rgb(37,40,95));
        TextView detail = new TextView(this);
        detail.setText(R.string.offline_detail);detail.setPadding(0,18,0,24);
        Button retry = new Button(this);
        retry.setText(R.string.retry);retry.setOnClickListener(view -> { offline.setVisibility(View.GONE); web.reload(); });
        offline.addView(title);offline.addView(detail);offline.addView(retry);
        root.addView(offline,new FrameLayout.LayoutParams(-1,-1));offline.setVisibility(View.GONE);
        if (Build.VERSION.SDK_INT >= 33) getOnBackInvokedDispatcher().registerOnBackInvokedCallback(0,this::back);
        if (state == null || web.restoreState(state) == null) web.loadUrl(HOME);
        if (state != null) pendingDownload=state.getString("pendingDownload");
    }

    private boolean navigate(Uri uri) {
        if (trusted(uri)) {
            String path=uri.getPath()==null?"":uri.getPath();
            if (path.startsWith("/api/") && (path.endsWith("/pdf") || path.endsWith("/recommendation") || path.endsWith("/report"))) {
                requestDownload(uri.toString(),"SIPAK-"+(path.endsWith("/recommendation")?"Rekomendasi":"Dokumen")+".pdf");return true;
            }
            return false;
        }
        if ("https".equalsIgnoreCase(uri.getScheme()) || "http".equalsIgnoreCase(uri.getScheme()) || "mailto".equalsIgnoreCase(uri.getScheme())) {
            try { startActivity(new Intent(Intent.ACTION_VIEW,uri)); } catch(ActivityNotFoundException error) { message("Tautan tidak dapat dibuka."); }
        }
        return true;
    }
    private void requestDownload(String url,String filename) {
        if (!trusted(Uri.parse(url))) { message("Unduhan harus berasal dari SIPAK.");return; }
        if (pendingDownload != null) { message("Selesaikan pilihan lokasi unduhan sebelumnya.");return; }
        pendingDownload=url;
        Intent intent=new Intent(Intent.ACTION_CREATE_DOCUMENT).addCategory(Intent.CATEGORY_OPENABLE).setType("application/pdf");
        intent.putExtra(Intent.EXTRA_TITLE,filename.replaceAll("[\\\\/:*?\"<>|]","_").substring(0,Math.min(filename.length(),120)));
        try { startActivityForResult(intent,SAVE_DOCUMENT); } catch(ActivityNotFoundException error) { pendingDownload=null;message("Penyimpanan file tidak tersedia."); }
    }
    @Override protected void onActivityResult(int request,int result,Intent data) {
        super.onActivityResult(request,result,data);
        if (request==CHOOSE_FILE && fileCallback!=null) {
            ArrayList<Uri> selected=new ArrayList<>();
            if (result==RESULT_OK && data!=null) {
                ClipData clips=data.getClipData();
                if (clips!=null) for(int i=0;i<clips.getItemCount();i++) selected.add(clips.getItemAt(i).getUri());
                else if(data.getData()!=null) selected.add(data.getData());
            }
            fileCallback.onReceiveValue(selected.isEmpty()?null:selected.toArray(new Uri[0]));fileCallback=null;
        }
        if (request==SAVE_DOCUMENT) {
            String source=pendingDownload;pendingDownload=null;
            if(result==RESULT_OK && data!=null && data.getData()!=null && source!=null) {
                Uri destination=data.getData();
                String cookie=CookieManager.getInstance().getCookie(source);
                downloads.execute(() -> download(source,destination,cookie));
                message("Mengunduh dokumen…");
            }
        }
    }
    private void download(String source,Uri destination,String cookie) {
        HttpURLConnection connection=null;
        try {
            connection=(HttpURLConnection)new URL(source).openConnection();
            connection.setInstanceFollowRedirects(false);connection.setConnectTimeout(20000);connection.setReadTimeout(120000);
            if(cookie!=null) connection.setRequestProperty("Cookie",cookie);
            if(connection.getResponseCode()!=200 || (connection.getContentType()==null || !connection.getContentType().toLowerCase(Locale.ROOT).contains("application/pdf"))) throw new java.io.IOException("Invalid PDF response");
            try(InputStream input=connection.getInputStream();OutputStream output=getContentResolver().openOutputStream(destination,"wt")) {
                if(output==null) throw new java.io.IOException("No output");
                byte[] buffer=new byte[32768];int count;
                while((count=input.read(buffer))!=-1) output.write(buffer,0,count);
            }
            runOnUiThread(() -> message("Dokumen tersimpan."));
        } catch(Exception error) {
            runOnUiThread(() -> new AlertDialog.Builder(this).setTitle("Unduhan belum berhasil").setMessage("Periksa koneksi dan sesi login, lalu unduh kembali.").setPositiveButton("Tutup",null).show());
        } finally { if(connection!=null) connection.disconnect(); }
    }
    private void showOffline() { navigationFailed=true;runOnUiThread(() -> offline.setVisibility(View.VISIBLE)); }
    private void message(String text) { Toast.makeText(this,text,Toast.LENGTH_LONG).show(); }
    private void back() { if(web.canGoBack()) web.goBack();else finish(); }
    @Override public void onBackPressed() { back(); }
    @Override protected void onSaveInstanceState(Bundle state) { web.saveState(state);state.putString("pendingDownload",pendingDownload);super.onSaveInstanceState(state); }
    @Override protected void onPause() { CookieManager.getInstance().flush();super.onPause(); }
    @Override protected void onDestroy() { if(fileCallback!=null)fileCallback.onReceiveValue(null);downloads.shutdown();web.destroy();super.onDestroy(); }
}
