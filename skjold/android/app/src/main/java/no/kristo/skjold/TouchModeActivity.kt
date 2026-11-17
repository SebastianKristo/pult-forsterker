package no.kristo.skjold

import android.annotation.SuppressLint
import android.app.Activity
import android.content.Context
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.net.http.SslError
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.text.InputType
import android.view.Gravity
import android.view.KeyEvent
import android.view.View
import android.view.ViewGroup
import android.view.WindowInsets
import android.view.WindowInsetsController
import android.view.WindowManager
import android.webkit.JavascriptInterface
import android.webkit.SslErrorHandler
import android.webkit.WebResourceError
import android.webkit.WebResourceRequest
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import android.widget.Toast

/**
 * Skjold Touch på et nettbrett (f.eks. Galaxy Tab A8): det samme grensesnittet som Skjold Touch, i fullskjerm.
 *
 * Nettbrettet er ikke en Skjold-enhet selv. Det laster `touch.html?fluid=1` fra en Skjold-enhet på nettet (S1, Touch,
 * Node), så grensesnittet styrer den enheten og rommene den ser – akkurat som Touch-skjermen. Grensesnittet fyller hele
 * skjermen, skjermspareren demper nettbrettets eget lys (window.SkjoldTablet.setBrightness), og skjermen holdes på.
 * Eget ikon («Skjold Touch») i appskuffen, ved siden av vanlige Skjold.
 */
class TouchModeActivity : Activity() {
    companion object {
        private const val PREFS = "skjold_touch"
        private const val KEY_BASE = "base"
    }

    private val main = Handler(Looper.getMainLooper())
    private var web: WebView? = null
    private var browser: DeviceBrowser? = null
    private var lastBack = 0L
    private val prefs by lazy { getSharedPreferences(PREFS, Context.MODE_PRIVATE) }

    private val bg = Color.parseColor("#0b0b0c")
    private val ink = Color.parseColor("#f2f2ee")
    private val dim = Color.parseColor("#8b8b86")
    private val gold = Color.parseColor("#d9a441")

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        window.decorView.setBackgroundColor(bg)
        val base = prefs.getString(KEY_BASE, null)
        if (base.isNullOrBlank()) showPicker() else showTouch(base)
    }

    override fun onWindowFocusChanged(hasFocus: Boolean) {
        super.onWindowFocusChanged(hasFocus)
        if (hasFocus) immersive()
    }

    private fun immersive() {
        if (android.os.Build.VERSION.SDK_INT >= 30) {
            window.setDecorFitsSystemWindows(false)
            window.insetsController?.let {
                it.hide(WindowInsets.Type.statusBars() or WindowInsets.Type.navigationBars())
                it.systemBarsBehavior = WindowInsetsController.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE
            }
        } else {
            @Suppress("DEPRECATION")
            window.decorView.systemUiVisibility = (View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY or View.SYSTEM_UI_FLAG_FULLSCREEN
                or View.SYSTEM_UI_FLAG_HIDE_NAVIGATION or View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN or View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION)
        }
    }

    // ---------- Touch-grensesnittet ----------
    @SuppressLint("SetJavaScriptEnabled")
    private fun showTouch(base: String) {
        stopBrowser()
        val w = WebView(this)
        w.setBackgroundColor(bg)
        w.settings.apply {
            javaScriptEnabled = true
            domStorageEnabled = true
            mediaPlaybackRequiresUserGesture = false   // fjord-skjermspareren (video) og ringeklokkelyd
            builtInZoomControls = false
            displayZoomControls = false
            setSupportZoom(false)
            useWideViewPort = true
            loadWithOverviewMode = false
        }
        w.isVerticalScrollBarEnabled = false
        w.isHorizontalScrollBarEnabled = false
        w.overScrollMode = View.OVER_SCROLL_NEVER
        w.addJavascriptInterface(Bridge(), "SkjoldTablet")
        w.webViewClient = object : WebViewClient() {
            override fun onReceivedError(view: WebView, req: WebResourceRequest, err: WebResourceError) {
                if (req.isForMainFrame) main.postDelayed({ view.loadUrl(url(base)) }, 5000)   // enheten starter kanskje på nytt
            }
            override fun onReceivedSslError(view: WebView, handler: SslErrorHandler, error: SslError) { handler.cancel() }
            override fun shouldOverrideUrlLoading(view: WebView, req: WebResourceRequest) = !req.url.toString().startsWith(base)
        }
        setContentView(w, ViewGroup.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT))
        web = w
        w.loadUrl(url(base))
        immersive()
    }

    private fun url(base: String) = base.trimEnd('/') + "/touch.html?fluid=1"

    /** Det Touch-grensesnittet kan be nettbrettet om. */
    inner class Bridge {
        @JavascriptInterface
        fun setBrightness(level: Int) {
            main.post {
                val lp = window.attributes
                // 0 = skjermen «av» (svart bilde, nesten mørkt baklys); ellers nettbrettets lysstyrke i prosent
                lp.screenBrightness = if (level <= 0) 0.01f else (level.coerceIn(5, 100) / 100f)
                window.attributes = lp
            }
        }

        @JavascriptInterface
        fun velgEnhet() { main.post { prefs.edit().remove(KEY_BASE).apply(); showPicker() } }

        @JavascriptInterface
        fun navn(): String = android.os.Build.MODEL ?: "Nettbrett"
    }

    // ---------- velg Skjold-enhet ----------
    private fun showPicker() {
        web?.let { it.stopLoading(); it.destroy() }
        web = null
        val lp = window.attributes; lp.screenBrightness = WindowManager.LayoutParams.BRIGHTNESS_OVERRIDE_NONE; window.attributes = lp

        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setBackgroundColor(bg)
            setPadding(dp(48), dp(40), dp(48), dp(32))
        }
        root.addView(TextView(this).apply {
            text = "SKJOLD TOUCH"; setTextColor(gold); textSize = 12f; letterSpacing = 0.16f; typeface = Typeface.MONOSPACE
        })
        root.addView(TextView(this).apply {
            text = "Velg Skjold-enheten nettbrettet skal styre"; setTextColor(ink); textSize = 26f; typeface = Typeface.DEFAULT_BOLD
            setPadding(0, dp(8), 0, dp(6))
        })
        root.addView(TextView(this).apply {
            text = "Nettbrettet viser det samme som Skjold Touch-skjermen og styrer enheten du velger, og rommene den ser. Nettbrettet må være på samme Wi-Fi."
            setTextColor(dim); textSize = 15f; setPadding(0, 0, 0, dp(20))
        })
        val list = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        val status = TextView(this).apply { text = "Leter etter Skjold-enheter …"; setTextColor(dim); textSize = 14f; setPadding(0, dp(4), 0, dp(12)) }
        root.addView(status)
        root.addView(ScrollView(this).apply { addView(list) }, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f))

        // skriv inn adressen selv (f.eks. 10.69.2.189)
        val manual = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL; gravity = Gravity.CENTER_VERTICAL; setPadding(0, dp(16), 0, 0) }
        val input = EditText(this).apply {
            hint = "Eller skriv adressen, f.eks. 10.69.2.189"; setHintTextColor(dim); setTextColor(ink); textSize = 16f
            inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_URI
            background = pill(Color.parseColor("#141415"), Color.parseColor("#2e2e30")); setPadding(dp(16), dp(12), dp(16), dp(12))
        }
        manual.addView(input, LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f))
        manual.addView(button("Koble til", primary = true) {
            val t = input.text.toString().trim()
            if (t.isEmpty()) return@button
            choose(if (t.startsWith("http")) t else "http://" + (if (t.contains(':')) t else "$t:8765"))
        }, LinearLayout.LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT).apply { leftMargin = dp(12) })
        root.addView(manual)
        setContentView(root)

        val b = DeviceBrowser(this); browser = b; b.start()
        var shown = ""
        val tick = object : Runnable {
            override fun run() {
                if (browser !== b) return
                val devs = b.devices.filter { it.host != null }
                val key = devs.joinToString { it.id + it.host }
                if (key != shown) {
                    shown = key; list.removeAllViews()
                    status.text = if (devs.isEmpty()) "Leter etter Skjold-enheter …" else "Fant ${devs.size} på nettet"
                    devs.forEach { d ->
                        list.addView(button(d.name + (if (d.product.isNotBlank()) "  ·  " + d.product.uppercase() else ""), primary = false) {
                            choose("http://" + d.host)
                        }, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(64)).apply { bottomMargin = dp(10) })
                    }
                }
                main.postDelayed(this, 1000)
            }
        }
        main.post(tick)
        immersive()
    }

    private fun choose(base: String) {
        prefs.edit().putString(KEY_BASE, base.trimEnd('/')).apply()
        showTouch(base.trimEnd('/'))
    }

    private fun stopBrowser() { browser?.stop(); browser = null }

    private fun button(label: String, primary: Boolean, onClick: () -> Unit) = Button(this).apply {
        text = label; isAllCaps = false; textSize = 17f; gravity = Gravity.CENTER_VERTICAL or Gravity.START
        setTextColor(if (primary) bg else ink)
        background = if (primary) pill(gold, gold) else pill(Color.parseColor("#141415"), Color.parseColor("#242426"))
        setPadding(dp(22), 0, dp(22), 0)
        if (primary) gravity = Gravity.CENTER
        setOnClickListener { onClick() }
    }

    private fun pill(fill: Int, stroke: Int) = GradientDrawable().apply {
        cornerRadius = dp(16).toFloat(); setColor(fill); setStroke(dp(1), stroke)
    }

    private fun dp(v: Int) = (v * resources.displayMetrics.density).toInt()

    // Tilbake: lukk bare med to trykk (skjermen står gjerne fast på veggen), i grensesnittet går tilbake én side
    override fun onKeyDown(keyCode: Int, event: KeyEvent?): Boolean {
        if (keyCode == KeyEvent.KEYCODE_BACK) {
            val now = System.currentTimeMillis()
            if (now - lastBack < 2000) { finish(); return true }
            lastBack = now
            Toast.makeText(this, "Trykk tilbake én gang til for å lukke Skjold Touch", Toast.LENGTH_SHORT).show()
            return true
        }
        return super.onKeyDown(keyCode, event)
    }

    override fun onResume() { super.onResume(); web?.onResume(); immersive() }
    override fun onPause() { web?.onPause(); super.onPause() }
    override fun onDestroy() { stopBrowser(); web?.destroy(); web = null; super.onDestroy() }
}
