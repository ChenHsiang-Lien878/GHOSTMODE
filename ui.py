import streamlit as st
from history import load_history, add_message, get_recent_history, format_history_for_prompt
from reply import generate_reply
from profile import get_display_name, generate_avatar


st.set_page_config(
    page_title="GhostMode",
    page_icon="👻",
    layout="wide"
)

# ---------------------------
# Session state
# ---------------------------
if "ghost_mode" not in st.session_state:
    st.session_state.ghost_mode = True

history_data = load_history()

# Build contacts from real saved history
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
            conversation = get_recent_history(selected_user)

            mode_label = "GhostMode ON" if st.session_state.ghost_mode else "GhostMode OFF"
            st.markdown(
                f'<span class="mode-pill">{mode_label}</span>'
                f'<span class="mode-pill">User ID: {selected_user}</span>',
                unsafe_allow_html=True
            )

            c1, c2 = st.columns([1, 4])
            with c1:
                if st.button("Toggle GhostMode"):
                    st.session_state.ghost_mode = not st.session_state.ghost_mode
                    st.rerun()

            st.divider()

            if conversation:
                for msg in conversation:
                    with st.chat_message(role_to_streamlit(msg["role"])):
                        st.write(msg["text"])
                        st.caption("User" if msg["role"] == "user" else "AI reply")
            else:
                st.info("No messages for this user.")

            st.divider()
            st.markdown("#### Reply Tools")

            user_input = st.text_area(
                "Manual Input",
                placeholder="Type a message to simulate a new incoming DM...",
                height=120
            )

            b1, b2 = st.columns(2)

            with b1:
                if st.button("Preview Reply", use_container_width=True):
                    if not user_input.strip():
                        st.warning("Enter a message first.")
                    else:
                        history_text = format_history_for_prompt(selected_user)
                        ai_reply = generate_reply(user_input, history_text)
                        st.success("Preview generated")
                        st.write(ai_reply)

            with b2:
                if st.button("Run GhostMode", use_container_width=True):
                    if not user_input.strip():
                        st.warning("Enter a message first.")
                    else:
                        # Save incoming user message
                        add_message(selected_user, "user", user_input)

                        if st.session_state.ghost_mode:
                            history_text = format_history_for_prompt(selected_user)
                            ai_reply = generate_reply(user_input, history_text)
                            add_message(selected_user, "assistant", ai_reply)
                            st.success("Reply generated and saved.")
                        else:
                            st.info("GhostMode is OFF. User message saved only.")

                        st.rerun()