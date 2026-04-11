import hashlib
import streamlit as st
from history import load_history, add_message, get_recent_history, format_history_for_prompt
from reply import generate_reply, send_reply
from profile import get_display_name
from settings import load_settings, save_settings
from streamlit_autorefresh import st_autorefresh

st.set_page_config(
    page_title="GhostMode",
    page_icon="👻",
    layout="wide"
)

st_autorefresh(interval=3000, key="ghostmode_refresh")

# ---------------------------
# Session state
# ---------------------------
settings = load_settings()

if "ghost_mode" not in st.session_state:
    st.session_state.ghost_mode = settings["ghost_mode"]

if "reply_mode" not in st.session_state:
    st.session_state.reply_mode = settings["reply_mode"]

if "reply_tone" not in st.session_state:
    st.session_state.reply_tone = settings["reply_tone"]

if "reply_delay_seconds" not in st.session_state:
    st.session_state.reply_delay_seconds = settings["reply_delay_seconds"]

if "manual_reply_text" not in st.session_state:
    st.session_state.manual_reply_text = ""

if "incoming_message_text" not in st.session_state:
    st.session_state.incoming_message_text = ""

if "clear_manual_reply" not in st.session_state:
    st.session_state.clear_manual_reply = False

if "clear_incoming_message" not in st.session_state:
    st.session_state.clear_incoming_message = False


# ---------------------------
# Settings callbacks
# ---------------------------
def on_delay_change():
    s = load_settings()
    s["reply_delay_seconds"] = st.session_state.reply_delay_seconds
    save_settings(s)

def on_tone_change():
    s = load_settings()
    s["reply_tone"] = st.session_state.reply_tone
    save_settings(s)

def on_reply_mode_change():
    s = load_settings()
    s["reply_mode"] = st.session_state.reply_mode
    save_settings(s)

def toggle_ghost_mode():
    st.session_state.ghost_mode = not st.session_state.ghost_mode
    s = load_settings()
    s["ghost_mode"] = st.session_state.ghost_mode
    save_settings(s)


# ---------------------------
# Data
# ---------------------------
history_data = load_history()
contact_ids = list(history_data.keys())

if "selected_user" not in st.session_state:
    st.session_state.selected_user = contact_ids[0] if contact_ids else None


# ---------------------------
# Helpers
# ---------------------------
def role_to_streamlit(role: str) -> str:
    return "user" if role == "user" else "assistant"

def message_count(user_id: str) -> int:
    return len(get_recent_history(user_id))

def last_message_preview(user_id: str) -> str:
    history = get_recent_history(user_id)
    if not history:
        return "No messages yet"
    text = history[-1]["text"]
    return text if len(text) <= 32 else text[:32] + "..."

def generate_avatar(name: str) -> str:
    initials = "".join([w[0] for w in name.split()[:2]]).upper() or "U"
    hash_color = hashlib.md5(name.encode()).hexdigest()[:6]
    return f"https://ui-avatars.com/api/?name={initials}&background={hash_color}&color=fff&size=128"


# ---------------------------
# Styling
# ---------------------------
st.markdown("""
<style>
.stApp {
    background:
        radial-gradient(circle at top left, rgba(108, 92, 231, 0.14), transparent 28%),
        radial-gradient(circle at top right, rgba(0, 212, 255, 0.10), transparent 24%),
        linear-gradient(135deg, #05070d 0%, #09111f 42%, #0c1630 100%);
    color: #f5f7fb;
}
/* Keep header visible but style it */
header {
    background-color: #05070d !important;
}

/* Inject custom title */
header::before {
    content: "👻 GhostMode";
    position: absolute;
    left: 20px;
    top: 10px;
    font-size: 1.2rem;
    font-weight: 700;
    color: white;
}

/* Optional: remove "Deploy" button */
[data-testid="stToolbar"] {
    right: 1rem;
}

.block-container {
    padding-top: 1.2rem;
    padding-bottom: 1.5rem;
    max-width: 1450px;
}

h1, h2, h3, h4 {
    color: white !important;
}

div[data-testid="stVerticalBlockBorderWrapper"] {
    background: rgba(12, 18, 34, 0.88);
    border: 1px solid rgba(126, 146, 189, 0.16) !important;
    border-radius: 24px !important;
    box-shadow: 0 12px 40px rgba(0, 0, 0, 0.22);
}

.hero-subtext {
    color: #94a0b5;
    margin-top: -0.45rem;
    margin-bottom: 1rem;
    font-size: 0.98rem;
}

.mode-pill {
    display: inline-block;
    padding: 0.38rem 0.8rem;
    margin-right: 0.45rem;
    margin-bottom: 0.65rem;
    border-radius: 999px;
    background: rgba(94, 220, 255, 0.10);
    border: 1px solid rgba(94, 220, 255, 0.28);
    color: #d5f8ff;
    font-size: 0.84rem;
    font-weight: 600;
}

.contact-card {
    display: flex;
    align-items: center;
    gap: 0.8rem;
    padding: 0.8rem 0.9rem;
    border-radius: 18px;
    border: 1px solid rgba(126, 146, 189, 0.12);
    background: rgba(255,255,255,0.025);
    margin-bottom: 0.7rem;
}

.contact-card:hover {
    border: 1px solid rgba(94,220,255,0.32);
    background: rgba(255,255,255,0.04);
}

.contact-name {
    font-weight: 700;
    color: #ffffff;
    margin-bottom: 0.15rem;
}

.contact-meta {
    color: #98a6bd;
    font-size: 0.84rem;
}

.section-label {
    color: #9fb0c9;
    font-size: 0.84rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 0.45rem;
    font-weight: 700;
}

.chat-shell {
    padding: 0.15rem 0 0.4rem 0;
}

div[data-baseweb="select"] > div,
div[data-testid="stNumberInputContainer"] input,
.stTextArea textarea {
    background-color: rgba(255,255,255,0.04) !important;
    color: white !important;
    border-radius: 14px !important;
    border: 1px solid rgba(120,140,180,0.18) !important;
}

.stButton button {
    border-radius: 14px !important;
    border: 1px solid rgba(126,146,189,0.16) !important;
    font-weight: 700 !important;
}

.primary-action button {
    background: linear-gradient(90deg, #6ee7ff 0%, #8b5cf6 100%) !important;
    color: #081018 !important;
    border: none !important;
}

.secondary-action button {
    background: rgba(255,255,255,0.04) !important;
    color: #f5f7fb !important;
}

[data-testid="stChatMessage"] {
    border-radius: 18px;
}

hr {
    border-color: rgba(126,146,189,0.12) !important;
}
</style>
""", unsafe_allow_html=True)


# ---------------------------
# Header
# ---------------------------
st.markdown("""
<div style="display:flex; align-items:center; gap:14px;">
    <div style="
        width:40px;
        height:40px;
        border-radius:12px;
        background: linear-gradient(135deg, #6ee7ff, #8b5cf6);
        display:flex;
        align-items:center;
        justify-content:center;
        font-size:20px;
    ">
        👻
    </div>
    <h1 style="margin:0;">GhostMode</h1>
</div>
""", unsafe_allow_html=True)
st.markdown(
    '<div class="hero-subtext">Autopilot messaging for overthinkers.</div>',
    unsafe_allow_html=True
)

left_col, right_col = st.columns([1.05, 2.6], gap="large")

# ---------------------------
# Left panel
# ---------------------------
with left_col:
    with st.container(border=True):
        st.markdown('<div class="section-label">Inbox</div>', unsafe_allow_html=True)

        history_data = load_history()
        contact_ids = list(history_data.keys())

        if not contact_ids:
            st.info("No chat history found yet. Send an Instagram message first.")
        else:
            for user_id in contact_ids:
                display_name, profile_pic = get_display_name(user_id)
                avatar_url = profile_pic if profile_pic else generate_avatar(display_name)
                preview = last_message_preview(user_id)

                card_col1, card_col2 = st.columns([1, 4])

                with card_col1:
                    st.image(avatar_url, width=44)

                with card_col2:
                    st.markdown(f"""
                    <div style="
                        padding: 10px 12px;
                        border-radius: 14px;
                        background: rgba(255,255,255,0.03);
                        border: 1px solid rgba(120,140,180,0.15);
                    ">
                        <div style="font-weight:700; color:white;">
                            {display_name}
                        </div>
                        <div style="font-size:0.75rem; color:#7f8aa3;">
                            {message_count(user_id)} messages
                        </div>
                        <div style="
                            font-size:0.85rem;
                            color:#94a0b5;   /* 👈 CHANGE THIS */
                            margin-top:4px;
                        ">
                            {preview}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    if st.button("Open", key=f"contact_{user_id}", use_container_width=True):
                        st.session_state.selected_user = user_id
                        st.rerun()

# ---------------------------
# Right panel
# ---------------------------
with right_col:
    with st.container(border=True):
        st.markdown('<div class="section-label">Conversation</div>', unsafe_allow_html=True)

        selected_user = st.session_state.selected_user

        if not selected_user:
            st.info("No user selected yet.")
        else:
            display_name, profile_pic = get_display_name(selected_user)
            avatar_url = profile_pic if profile_pic else generate_avatar(display_name)
            conversation = get_recent_history(selected_user)

            # Header
            header_col1, header_col2, header_col3 = st.columns([1, 5, 2])

            with header_col1:
                st.image(avatar_url, width=62)

            with header_col2:
                st.markdown(f"### {display_name}")
                st.caption(f"Instagram ID: {selected_user}")

            with header_col3:
                st.button(
                    "GhostMode ON" if st.session_state.ghost_mode else "GhostMode OFF",
                    on_click=toggle_ghost_mode,
                    use_container_width=True
                )

            st.markdown(
                f'<span class="mode-pill">Mode: {st.session_state.reply_mode.title()}</span>'
                f'<span class="mode-pill">Tone: {st.session_state.reply_tone.title()}</span>'
                f'<span class="mode-pill">Delay: {st.session_state.reply_delay_seconds}s</span>',
                unsafe_allow_html=True
            )

            # Controls row
            control_col1, control_col2, control_col3 = st.columns([1, 1, 1])

            with control_col1:
                st.selectbox(
                    "Reply Mode",
                    ["normal", "no"],
                    key="reply_mode",
                    on_change=on_reply_mode_change
                )

            with control_col2:
                st.selectbox(
                    "Reply Tone",
                    ["casual", "formal"],
                    key="reply_tone",
                    on_change=on_tone_change
                )

            with control_col3:
                st.number_input(
                    "Reply Delay (seconds)",
                    min_value=0,
                    max_value=120,
                    step=1,
                    key="reply_delay_seconds",
                    on_change=on_delay_change
                )

            st.divider()

            # Chat history
            if conversation:
                chat_box = st.container(height=430, border=False)
                with chat_box:
                    for msg in conversation:
                        with st.chat_message(role_to_streamlit(msg["role"])):
                            st.write(msg["text"])

                            if msg["role"] == "user":
                                st.caption(display_name)
                            elif msg["role"] == "manual":
                                st.caption("You")
                            elif msg["role"] == "pending":
                                st.caption("GhostMode AI • sending soon...")
                            else:
                                st.caption("GhostMode AI")
            else:
                st.info("No messages for this user.")

            st.divider()

            st.markdown('<div class="section-label">Reply Tools</div>', unsafe_allow_html=True)

            # clear flags BEFORE widgets
            if st.session_state.clear_incoming_message:
                st.session_state.incoming_message_text = ""
                st.session_state.clear_incoming_message = False

            if st.session_state.clear_manual_reply:
                st.session_state.manual_reply_text = ""
                st.session_state.clear_manual_reply = False

            compose_col1, compose_col2 = st.columns([1, 1])

            with compose_col1:
                st.text_area(
                    "Incoming Message Simulator",
                    placeholder="Simulate a new incoming DM...",
                    height=110,
                    key="incoming_message_text"
                )

            with compose_col2:
                st.text_area(
                    "Manual Reply",
                    placeholder="Write your own reply to this contact...",
                    height=110,
                    key="manual_reply_text"
                )

            action_col1, action_col2, action_col3 = st.columns(3)

            with action_col1:
                st.markdown('<div class="secondary-action">', unsafe_allow_html=True)
                preview_clicked = st.button("Preview Reply", use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)

            with action_col2:
                st.markdown('<div class="primary-action">', unsafe_allow_html=True)
                run_clicked = st.button("Run GhostMode", use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)

            with action_col3:
                st.markdown('<div class="secondary-action">', unsafe_allow_html=True)
                send_clicked = st.button("Send Manual Reply", use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)

            if preview_clicked:
                if not st.session_state.incoming_message_text.strip():
                    st.warning("Enter an incoming message first.")
                else:
                    history_text = format_history_for_prompt(selected_user)
                    ai_reply = generate_reply(
                        st.session_state.incoming_message_text,
                        history_text,
                        st.session_state.reply_mode,
                        st.session_state.reply_tone
                    )
                    st.success("Preview generated")
                    st.write(ai_reply)

            if run_clicked:
                if not st.session_state.incoming_message_text.strip():
                    st.warning("Enter an incoming message first.")
                else:
                    add_message(selected_user, "user", st.session_state.incoming_message_text)

                    if st.session_state.ghost_mode:
                        history_text = format_history_for_prompt(selected_user)
                        ai_reply = generate_reply(
                            st.session_state.incoming_message_text,
                            history_text,
                            st.session_state.reply_mode,
                            st.session_state.reply_tone
                        )
                        add_message(selected_user, "assistant", ai_reply)
                        st.success("GhostMode reply generated and saved.")
                    else:
                        st.info("GhostMode is OFF. User message saved only.")

                    st.session_state.clear_incoming_message = True
                    st.rerun()

            if send_clicked:
                if not st.session_state.manual_reply_text.strip():
                    st.warning("Type a manual reply first.")
                else:
                    manual_text = st.session_state.manual_reply_text
                    ok, result = send_reply(selected_user, manual_text)

                    if ok:
                        add_message(selected_user, "manual", manual_text)
                        st.success("Manual reply sent.")
                        st.session_state.clear_manual_reply = True
                        st.rerun()
                    else:
                        st.error(f"Failed to send reply: {result}")