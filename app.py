import streamlit as st

st.set_page_config(
    page_title="GhostMode",
    page_icon=None,
    layout="wide"
)

st.markdown("""
<style>
.stApp {
    background: linear-gradient(135deg, #05070d 0%, #09111f 45%, #0c1630 100%);
    color: #f5f7fb;
}

.block-container {
    padding-top: 1.2rem;
    padding-bottom: 2rem;
    max-width: 1400px;
}

h1, h2, h3, h4 {
    color: white !important;
}

section[data-testid="stSidebar"] {
    background: #0b1220;
}

div[data-testid="stVerticalBlockBorderWrapper"] {
    background: rgba(13, 20, 38, 0.92);
    border: 1px solid rgba(120, 140, 180, 0.18) !important;
    border-radius: 24px !important;
    box-shadow: 0 12px 40px rgba(0, 0, 0, 0.22);
}

.mode-pill {
    display: inline-block;
    padding: 0.35rem 0.75rem;
    margin-right: 0.45rem;
    margin-bottom: 0.7rem;
    border-radius: 999px;
    background: rgba(94, 220, 255, 0.10);
    border: 1px solid rgba(94, 220, 255, 0.35);
    color: #d5f8ff;
    font-size: 0.85rem;
}

.contact-card {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(120,140,180,0.18);
    border-radius: 18px;
    padding: 0.9rem 1rem;
    margin-bottom: 0.8rem;
}

.contact-card.active {
    border: 1px solid rgba(94,220,255,0.85);
    box-shadow: 0 0 16px rgba(94,220,255,0.10);
}

.contact-name {
    font-weight: 700;
    color: #ffffff;
    margin-bottom: 0.2rem;
    font-size: 1rem;
}

.contact-meta {
    color: #9ca7ba;
    font-size: 0.92rem;
}

.section-label {
    color: #9fb0c9;
    font-size: 0.9rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 0.4rem;
}

.hero-subtext {
    color: #94a0b5;
    margin-top: -0.4rem;
    margin-bottom: 1.2rem;
}

.stTextArea textarea {
    background: rgba(255,255,255,0.03) !important;
    color: white !important;
    border-radius: 16px !important;
    border: 1px solid rgba(120,140,180,0.18) !important;
}

div[data-baseweb="select"] > div {
    background-color: rgba(255,255,255,0.04) !important;
    border-radius: 14px !important;
    border: 1px solid rgba(120,140,180,0.18) !important;
}

.stButton button {
    background: linear-gradient(90deg, #6ee7ff 0%, #8b5cf6 100%);
    color: #081018;
    border: none;
    border-radius: 14px;
    font-weight: 700;
    padding: 0.65rem 1.2rem;
}

.stButton button:hover {
    filter: brightness(1.05);
}

[data-testid="stCaptionContainer"] {
    color: #9ca7ba;
}
</style>
""", unsafe_allow_html=True)

st.title("GhostMode")
st.markdown('<div class="hero-subtext">Autopilot messaging for overthinkers.</div>', unsafe_allow_html=True)

left_col, right_col = st.columns([1, 2.5], gap="large")

with left_col:
    with st.container(border=True):
        st.markdown('<div class="section-label">Sidebar</div>', unsafe_allow_html=True)
        st.subheader("Contacts")

        st.markdown("""
        <div class="contact-card active">
            <div class="contact-name">Alex</div>
            <div class="contact-meta">GhostMode off • 14 messages</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div class="contact-card">
            <div class="contact-name">Mia</div>
            <div class="contact-meta">Normal mode • 5 messages</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div class="contact-card">
            <div class="contact-name">Sam</div>
            <div class="contact-meta">Ghost mode • 8 messages</div>
        </div>
        """, unsafe_allow_html=True)

with right_col:
    with st.container(border=True):
        st.markdown('<div class="section-label">Chat Header</div>', unsafe_allow_html=True)
        st.markdown("### Alex")
        st.caption("Active now • Last interaction 3 minutes ago")

        st.markdown(
            '<span class="mode-pill">Mode: No mode</span>'
            '<span class="mode-pill">Delay: 3s–3s</span>',
            unsafe_allow_html=True
        )

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="section-label">Conversation</div>', unsafe_allow_html=True)

        with st.chat_message("assistant"):
            st.write("Can you make dinner tonight?")
            st.caption("08:27 PM | Alex")

        with st.chat_message("assistant"):
            st.write("Hi Ilkut, do you want to meet up tonight?")
            st.caption("08:34 PM | Alex")

        with st.chat_message("user"):
            st.write("Sounds good, yeah that works for me, I can do that.")
            st.caption("08:34 PM | You | AI reply sent after 35s")

        with st.chat_message("assistant"):
            st.write("Hey, wanna meet up tonight?")
            st.caption("09:57 PM | Alex")

        with st.chat_message("assistant"):
            st.write("Hi, how are you?")
            st.caption("09:57 PM | Alex")

        with st.chat_message("user"):
            st.write("Yo, I’m good. Noted on my side.")
            st.caption("09:57 PM | You | AI reply sent after 3s")

        st.divider()

        st.markdown('<div class="section-label">Compose</div>', unsafe_allow_html=True)

        mode = st.selectbox(
            "Select Mode",
            ["Tone Analyzer", "Reply Generator", "Decision Helper"]
        )

        user_input = st.text_area(
            "Message Input",
            placeholder="Paste a message or describe a situation...",
            height=120
        )

        button_col, _ = st.columns([1, 4])
        with button_col:
            st.button("Run GhostMode")