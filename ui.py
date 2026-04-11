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

if "manual_reply_text" not in st.session_state:
    st.session_state.manual_reply_text = ""

if "incoming_message_text" not in st.session_state:
    st.session_state.incoming_message_text = ""

if "clear_manual_reply" not in st.session_state:
    st.session_state.clear_manual_reply = False

if "clear_incoming_message" not in st.session_state:
    st.session_state.clear_incoming_message = False

settings = load_settings()

if "reply_delay_seconds" not in st.session_state:
    st.session_state.reply_delay_seconds = settings["reply_delay_seconds"]

def on_delay_change():
    settings = load_settings()
    settings["reply_delay_seconds"] = st.session_state.reply_delay_seconds
    save_settings(settings)



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

.hero-subtext {
    color: #94a0b5;
    margin-top: -0.4rem;
    margin-bottom: 1.2rem;
    
.chat-scroll-box {
    height: 420px;
    overflow-y: auto;
    padding-right: 0.5rem;
    border-radius: 16px;
}
</style>
""", unsafe_allow_html=True)

# ---------------------------
# Header
# ---------------------------
st.title("GhostMode")
st.markdown(
    '<div class="hero-subtext">Autopilot messaging for overthinkers.</div>',
    unsafe_allow_html=True
)

left_col, right_col = st.columns([1, 2.5], gap="large")

# ---------------------------
# Left panel: contacts
# ---------------------------
with left_col:
    with st.container(border=True):
        st.markdown("#### Real Conversations")

        history_data = load_history()
        contact_ids = list(history_data.keys())

        if not contact_ids:
            st.info("No chat history found yet. Send an Instagram message first.")
        else:
            for user_id in contact_ids:
                display_name, profile_pic = get_display_name(user_id)

                col1, col2 = st.columns([1, 4])

                with col1:
                    avatar_url = profile_pic if profile_pic else generate_avatar(display_name)
                    st.image(avatar_url, width=40)

                with col2:
                    label = f"{display_name} • {message_count(user_id)} msgs"
                    if st.button(label, key=f"contact_{user_id}", use_container_width=True):
                        st.session_state.selected_user = user_id
                        st.rerun()

# ---------------------------
# Right panel: chat + controls
# ---------------------------
with right_col:
    with st.container(border=True):
        st.markdown("#### Chat Viewer")

        selected_user = st.session_state.selected_user

        if not selected_user:
            st.info("No user selected yet.")
        else:
            display_name, profile_pic = get_display_name(selected_user)
            conversation = get_recent_history(selected_user)

            header_col1, header_col2 = st.columns([1, 6])

            with header_col1:
                avatar_url = profile_pic if profile_pic else generate_avatar(display_name)
                st.image(avatar_url, width=60)

            with header_col2:
                st.markdown(f"### {display_name}")
                st.caption(f"Instagram ID: {selected_user}")

            mode_label = "GhostMode ON" if st.session_state.ghost_mode else "GhostMode OFF"
            st.markdown(
                f'<span class="mode-pill">{mode_label}</span>'
                f'<span class="mode-pill">{display_name}</span>'
                f'<span class="mode-pill">Delay: {st.session_state.reply_delay_seconds}s</span>'
                f'<span class="mode-pill">Mode: {st.session_state.reply_mode.title()}</span>',

                unsafe_allow_html=True
            )

            from settings import load_settings, save_settings

            if "reply_mode" not in st.session_state:
                st.session_state.reply_mode = load_settings()["reply_mode"]


            def on_reply_mode_change():
                settings = load_settings()
                settings["reply_mode"] = st.session_state.reply_mode
                save_settings(settings)


            toggle_col, _ = st.columns([1, 4])
            with toggle_col:
                if st.button("Toggle GhostMode"):
                    st.session_state.ghost_mode = not st.session_state.ghost_mode

                    settings = load_settings()
                    settings["ghost_mode"] = st.session_state.ghost_mode
                    save_settings(settings)

                    st.rerun()


            st.selectbox(
                "Reply Mode",
                ["normal", "no"],
                key="reply_mode",
                on_change=on_reply_mode_change
            )


            st.number_input(
                "Reply Delay (seconds)",
                min_value=0,
                max_value=120,
                step=1,
                key="reply_delay_seconds",
                on_change=on_delay_change
            )

            st.divider()

            st.divider()

            if conversation:
                chat_box = st.container(height=420, border=False)

                with chat_box:
                    for msg in conversation:
                        with st.chat_message(role_to_streamlit(msg["role"])):
                            st.write(msg["text"])

                            if msg["role"] == "user":
                                st.caption(display_name)
                            elif msg["role"] == "manual":
                                st.caption("You")
                            else:
                                st.caption("GhostMode AI")
            else:
                st.info("No messages for this user.")

            st.divider()
            st.markdown("#### Reply Tools")

            # Clear flags must be handled BEFORE widgets are created
            if st.session_state.clear_incoming_message:
                st.session_state.incoming_message_text = ""
                st.session_state.clear_incoming_message = False

            if st.session_state.clear_manual_reply:
                st.session_state.manual_reply_text = ""
                st.session_state.clear_manual_reply = False

            st.text_area(
                "Incoming Message Simulator",
                placeholder="Type a message to simulate a new incoming DM...",
                height=120,
                key="incoming_message_text"
            )

            st.text_area(
                "Manual Reply",
                placeholder="Type your own reply to send to this contact...",
                height=100,
                key="manual_reply_text"
            )

            b1, b2, b3 = st.columns(3)

            with b1:
                if st.button("Preview Reply", use_container_width=True):
                    if not st.session_state.incoming_message_text.strip():
                        st.warning("Enter an incoming message first.")
                    else:
                        print("Current reply mode:", st.session_state.reply_mode, flush=True)
                        history_text = format_history_for_prompt(selected_user)
                        ai_reply = generate_reply(
                            st.session_state.incoming_message_text,
                            history_text,
                            st.session_state.reply_mode
                        )
                        st.success("Preview generated")
                        st.write(ai_reply)

            with b2:
                if st.button("Run GhostMode", use_container_width=True):
                    if not st.session_state.incoming_message_text.strip():
                        st.warning("Enter an incoming message first.")
                    else:
                        add_message(selected_user, "user", st.session_state.incoming_message_text)

                        if st.session_state.ghost_mode:
                            history_text = format_history_for_prompt(selected_user)
                            ai_reply = generate_reply(
                                st.session_state.incoming_message_text,
                                history_text,
                                st.session_state.reply_mode
                            )
                            add_message(selected_user, "assistant", ai_reply)
                            st.success("GhostMode reply generated and saved.")
                        else:
                            st.info("GhostMode is OFF. User message saved only.")

                        st.session_state.clear_incoming_message = True
                        st.rerun()

            with b3:
                if st.button("Send Manual Reply", use_container_width=True):
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