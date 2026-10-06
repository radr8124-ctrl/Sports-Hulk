import streamlit as st


def apply_premium_theme():

    st.html(
        """
<style>

/* =========================================================
   SPORTS HULK — LIGHT PREMIUM
   ========================================================= */

:root {
    --bg: #f4f7fb;
    --surface: #ffffff;
    --surface-soft: #eef3fa;

    --navy: #10233f;
    --navy-2: #173b69;

    --text: #15233a;
    --muted: #697a91;

    --blue: #3f7cff;
    --cyan: #28a9df;
    --green: #18a873;
    --amber: #e5a52e;
    --red: #e45262;
    --purple: #8259dc;

    --border: #dde6f1;

    --shadow:
        0 10px 28px rgba(38,67,105,.10);

    --shadow-hover:
        0 16px 38px rgba(38,67,105,.16);
}


/* PAGE */

.stApp {
    background:
        linear-gradient(
            180deg,
            #f7f9fc 0%,
            #f3f6fb 100%
        );

    color:
        var(--text);
}

.block-container {
    max-width:
        1420px;

    padding-top:
        1rem;

    padding-bottom:
        4rem;
}


/* TYPOGRAPHY */

h1,
h2,
h3,
p,
label {
    font-family:
        Inter,
        -apple-system,
        BlinkMacSystemFont,
        "Segoe UI",
        sans-serif;
}


/* BRAND */

.sh-brand-row {
    display:
        flex;

    justify-content:
        space-between;

    align-items:
        center;

    padding:
        15px 19px;

    margin-bottom:
        12px;

    border-radius:
        18px;

    background:
        linear-gradient(
            120deg,
            #10233f,
            #194f8e 58%,
            #3d78dd
        );

    box-shadow:
        0 10px 30px rgba(28,69,123,.19);
}

.sh-brand {
    color:
        #ffffff;

    font-size:
        15px;

    font-weight:
        850;

    letter-spacing:
        .13em;
}

.sh-live {
    display:
        inline-flex;

    align-items:
        center;

    gap:
        7px;

    padding:
        6px 10px;

    border-radius:
        999px;

    color:
        #ffffff;

    background:
        rgba(255,255,255,.13);

    border:
        1px solid rgba(255,255,255,.20);

    font-size:
        11px;

    font-weight:
        750;
}

.sh-live-dot {
    width:
        7px;

    height:
        7px;

    border-radius:
        50%;

    background:
        #4de3ac;

    box-shadow:
        0 0 10px rgba(77,227,172,.8);
}


/* HERO */

.sh-hero {
    position:
        relative;

    overflow:
        hidden;

    padding:
        22px 24px;

    margin:
        8px 0 13px;

    border-radius:
        20px;

    background:
        linear-gradient(
            135deg,
            #ffffff,
            #f0f5fd
        );

    border:
        1px solid var(--border);

    box-shadow:
        var(--shadow);
}

.sh-kicker {
    color:
        var(--blue);

    font-size:
        11px;

    font-weight:
        800;

    letter-spacing:
        .09em;

    text-transform:
        uppercase;

    margin-bottom:
        6px;
}

.sh-hero-title {
    color:
        var(--navy);

    font-size:
        clamp(26px,3vw,37px);

    font-weight:
        820;

    letter-spacing:
        -.035em;

    line-height:
        1.05;
}

.sh-hero-sub {
    color:
        var(--muted);

    margin-top:
        8px;

    font-size:
        13px;

    line-height:
        1.55;
}


/* EXPLAINER */

.sh-explainer {
    display:
        flex;

    align-items:
        flex-start;

    gap:
        10px;

    margin:
        9px 0 17px;

    padding:
        12px 14px;

    border-radius:
        13px;

    color:
        #46617f;

    background:
        #eaf2ff;

    border:
        1px solid #cfe0fb;
}

.sh-explainer-icon {
    display:
        flex;

    align-items:
        center;

    justify-content:
        center;

    width:
        23px;

    height:
        23px;

    flex:
        0 0 auto;

    border-radius:
        7px;

    color:
        white;

    background:
        var(--blue);

    font-size:
        12px;

    font-weight:
        800;
}

.sh-explainer-text {
    color:
        #536b88;

    font-size:
        12px;

    line-height:
        1.5;
}


/* SECTION */

.sh-section {
    display:
        flex;

    justify-content:
        space-between;

    align-items:
        end;

    margin:
        22px 0 10px;
}

.sh-section-title {
    color:
        var(--navy);

    font-size:
        19px;

    font-weight:
        790;
}

.sh-section-sub {
    color:
        var(--muted);

    font-size:
        12px;

    margin-top:
        2px;
}


/* CARDS */

.sh-card,
.sh-premium-card {
    position:
        relative;

    overflow:
        hidden;

    min-height:
        172px;

    padding:
        17px;

    margin-bottom:
        11px;

    border-radius:
        17px;

    background:
        var(--surface);

    border:
        1px solid var(--border);

    box-shadow:
        var(--shadow);

    transition:
        transform .16s ease,
        box-shadow .16s ease,
        border-color .16s ease;
}

.sh-card:hover,
.sh-premium-card:hover {
    transform:
        translateY(-2px);

    box-shadow:
        var(--shadow-hover);

    border-color:
        #c9d8ea;
}

.sh-card-accent {
    position:
        absolute;

    left:
        0;

    top:
        0;

    bottom:
        0;

    width:
        4px;

    background:
        var(--card-accent,#3f7cff);
}

.sh-card-eyebrow {
    color:
        #7a8da5;

    font-size:
        10px;

    font-weight:
        800;

    letter-spacing:
        .08em;

    text-transform:
        uppercase;

    margin-bottom:
        6px;
}

.sh-card-title {
    color:
        var(--navy);

    font-size:
        15px;

    font-weight:
        760;

    line-height:
        1.25;
}

.sh-card-headline {
    color:
        #13233b;

    font-size:
        23px;

    font-weight:
        840;

    letter-spacing:
        -.03em;

    line-height:
        1.12;

    margin-top:
        7px;
}

.sh-card-copy,
.sh-card-body {
    color:
        var(--muted);

    font-size:
        12px;

    line-height:
        1.5;

    margin:
        8px 0;
}


/* CHIPS */

.sh-chip {
    display:
        inline-flex;

    align-items:
        center;

    padding:
        5px 8px;

    margin:
        2px 4px 2px 0;

    border-radius:
        999px;

    font-size:
        10px;

    font-weight:
        760;
}

.sh-chip-blue {
    color:
        #285ebd;

    background:
        #e7efff;
}

.sh-chip-green {
    color:
        #087a51;

    background:
        #ddf7ed;
}

.sh-chip-amber {
    color:
        #9b6713;

    background:
        #fff2d7;
}

.sh-chip-red {
    color:
        #a93341;

    background:
        #ffe5e9;
}

.sh-chip-purple {
    color:
        #6540b0;

    background:
        #efe8ff;
}


/* METRICS */

[data-testid="stMetric"] {
    padding:
        15px;

    border-radius:
        15px;

    background:
        #ffffff;

    border:
        1px solid var(--border);

    box-shadow:
        var(--shadow);
}

[data-testid="stMetricLabel"] p {
    color:
        var(--muted) !important;
}

[data-testid="stMetricValue"] {
    color:
        var(--navy) !important;

    font-weight:
        820 !important;
}


/* BUTTONS */

.stButton > button,
.stDownloadButton > button {
    min-height:
        40px;

    border-radius:
        11px !important;

    border:
        1px solid #d5e0ee !important;

    background:
        #ffffff !important;

    color:
        #24405f !important;

    font-weight:
        690 !important;

    box-shadow:
        0 4px 13px rgba(39,66,98,.07);
}

.stButton > button:hover {
    border-color:
        #7fa8e8 !important;

    color:
        #1d5fc3 !important;

    background:
        #f3f7ff !important;
}

button[kind="primary"] {
    color:
        #ffffff !important;

    background:
        linear-gradient(
            135deg,
            #3979eb,
            #5e72e8
        ) !important;

    border:
        none !important;
}


/* RADIO NAVIGATION */

div[role="radiogroup"] label {
    background:
        #ffffff !important;

    border:
        1px solid #dce5f0 !important;

    border-radius:
        999px !important;

    color:
        #405873 !important;
}

div[role="radiogroup"] label:has(
    input:checked
) {
    background:
        #e8f0ff !important;

    border-color:
        #9bbdf2 !important;
}

div[role="radiogroup"] p {
    color:
        #405873 !important;

    font-weight:
        700 !important;
}


/* TABLES */

[data-testid="stDataFrame"] {
    border:
        1px solid var(--border);

    border-radius:
        15px;

    overflow:
        hidden;

    background:
        #ffffff;

    box-shadow:
        var(--shadow);
}


/* EXPANDERS */

[data-testid="stExpander"] {
    background:
        #ffffff;

    border:
        1px solid var(--border);

    border-radius:
        14px;
}


/* MOBILE */

@media (max-width:768px) {

    .block-container {
        padding-left:
            .85rem;

        padding-right:
            .85rem;
    }

    .sh-brand-row {
        border-radius:
            14px;
    }

    .sh-hero {
        padding:
            18px;

        border-radius:
            16px;
    }

    .sh-hero-title {
        font-size:
            25px;
    }

    .sh-card,
    .sh-premium-card {
        min-height:
            150px;

        padding:
            14px;
    }

}

</style>
        """
    )
