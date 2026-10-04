"""
Promise Tracker - Best Use of Google Gemma (Gemini API)
Hackathon Challenge Prototype - Clean Production Ready
"""

import os
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

import streamlit as st
import html
import json
from datetime import date, timedelta

from config import DEFAULT_GEMMA_MODEL, AVAILABLE_GEMMA_MODELS, GEMMA_SYSTEM_PROMPT
from extractor import (
    CommitmentItem,
    UnresolvedItem,
    ExtractionResult,
    verify_quote_in_text,
)
from gemma_client import GemmaClient
from utils import (
    highlight_transcript_with_quotes,
    export_commitments_to_csv,
    export_commitments_to_markdown,
    next_task_id,
)
from styles import CUSTOM_CSS
from sample_data import SAMPLE_CONVERSATIONS
from storage import (
    get_persisted_api_key,
    persist_api_key,
    load_saved_board,
    save_current_board,
    clear_persisted_board,
)

# Page configuration
st.set_page_config(
    page_title="Promise Tracker | Google Gemma",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Inject custom CSS
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# Load persisted board state if exists
try:
    saved_state = load_saved_board()
except (OSError, json.JSONDecodeError):
    st.error(
        "Could not load saved_board_state.json. The file may be unreadable or "
        "invalid JSON; restore a valid copy or repair it, then restart the app."
    )
    st.stop()

# Initialize Session State
if "commitments" not in st.session_state:
    raw_c = saved_state.get("commitments", [])
    st.session_state.commitments = [CommitmentItem(**c) if isinstance(c, dict) else c for c in raw_c]
if "unresolved_items" not in st.session_state:
    raw_u = saved_state.get("unresolved_items", [])
    st.session_state.unresolved_items = [UnresolvedItem(**u) if isinstance(u, dict) else u for u in raw_u]
if "raw_transcript" not in st.session_state:
    st.session_state.raw_transcript = saved_state.get("raw_transcript", "")
if "extraction_result" not in st.session_state:
    raw_e = saved_state.get("extraction_result")
    st.session_state.extraction_result = ExtractionResult(**raw_e) if isinstance(raw_e, dict) else raw_e
if "filter_person" not in st.session_state:
    st.session_state.filter_person = "All"
if "filter_status" not in st.session_state:
    st.session_state.filter_status = "All"
def sync_persistence():
    """Helper to save current board changes permanently."""
    save_current_board(
        commitments=st.session_state.commitments,
        unresolved_items=st.session_state.unresolved_items,
        raw_transcript=st.session_state.raw_transcript,
        extraction_result=st.session_state.extraction_result
    )


def clear_board():
    """Clear the board and transcript before their widgets are recreated."""
    st.session_state.commitments = []
    st.session_state.unresolved_items = []
    st.session_state.raw_transcript = ""
    st.session_state.extraction_result = None
    clear_persisted_board()


def html_text(value: object) -> str:
    """Escape untrusted text before placing it in custom HTML."""
    return html.escape(str(value), quote=True)


def save_task_change(task: CommitmentItem, before: dict) -> None:
    after = task.model_dump(mode="json")
    changes = {
        key: value
        for key, value in after.items()
        if before.get(key) != value
    }
    if changes:
        sync_persistence()


# --- SIDEBAR CONFIGURATION ---
with st.sidebar:
    st.markdown("""
        <div style="display:flex; align-items:center; gap:10px; margin-bottom: 12px;">
            <span style="font-size: 1.8rem;">✦</span>
            <div>
                <h3 style="margin:0; font-size:1.2rem; font-weight:800;">Promise Tracker</h3>
                <span style="font-size:0.75rem; color:#64748b; font-weight:600;">CHALLENGE 01: BEST USE OF GEMMA 4</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("🤖 Gemma Model Settings")
    
    selected_model = st.selectbox(
        "Gemma Model Endpoint:",
        options=AVAILABLE_GEMMA_MODELS,
        index=AVAILABLE_GEMMA_MODELS.index(DEFAULT_GEMMA_MODEL),
        help="Choose one of the Gemma 4 endpoints supported by the Gemini API."
    )
    custom_model_toggle = st.checkbox("Custom Model Name Override", value=False)
    if custom_model_toggle:
        selected_model = st.text_input("Model ID:", value=selected_model)

    # API Key Input with auto-persistence
    persisted_key = get_persisted_api_key()
    api_key_input = st.text_input(
        "Google Gemini API Key:",
        type="password",
        value=persisted_key,
        placeholder="AIzaSy...",
        help="Enter your Gemini API key from Google AI Studio. It will be saved permanently so you never lose it on refresh."
    )
    if api_key_input and api_key_input.strip() and api_key_input.strip() != persisted_key:
        persist_api_key(api_key_input.strip())
        st.sidebar.success("💾 API Key saved permanently!")
    elif persisted_key:
        st.sidebar.caption("🔒 Saved API Key active")

    temperature = st.slider(
        "Extraction Temperature:",
        min_value=0.0,
        max_value=0.7,
        value=0.1,
        step=0.05,
        help="Lower values reduce output variability; they do not prevent mistakes or hallucinations."
    )

    st.markdown("---")
    st.markdown("""
        <div style="background: rgba(66, 133, 244, 0.08); border-radius: 8px; padding: 12px; font-size: 0.8rem; border-left: 3px solid #4285F4;">
            <b>How to Run:</b><br/>
            1. Enter your Google Gemini API Key above.<br/>
            2. Paste any Slack, WhatsApp, Teams, or meeting chat into the main window.<br/>
            3. Click <b>Extract Commitments with Gemma</b>.<br/>
            4. Review the proposed tasks and quote checks before acting on them.
        </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.caption("Connect with me")
    st.markdown(
        """
        <div style="display:flex; flex-wrap:wrap; gap:12px; align-items:center;">
            <a href="https://github.com/amantdevio" target="_blank" rel="noopener noreferrer"
               aria-label="GitHub" style="display:inline-flex; align-items:center; gap:5px; text-decoration:none;">
                <svg width="18" height="18" viewBox="0 0 16 16" aria-hidden="true" fill="currentColor">
                    <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82a7.65 7.65 0 0 1 4 0c1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0 0 16 8c0-4.42-3.58-8-8-8"/>
                </svg> GitHub
            </a>
            <a href="https://www.instagram.com/amantdevio/" target="_blank" rel="noopener noreferrer"
               aria-label="Instagram" style="display:inline-flex; align-items:center; gap:5px; text-decoration:none;">
                <svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2">
                    <rect x="3" y="3" width="18" height="18" rx="5"/>
                    <circle cx="12" cy="12" r="4"/>
                    <circle cx="18" cy="6" r="1" fill="currentColor" stroke="none"/>
                </svg> Instagram
            </a>
            <a href="https://www.linkedin.com/in/amantdevio/" target="_blank" rel="noopener noreferrer"
               aria-label="LinkedIn" style="display:inline-flex; align-items:center; gap:5px; text-decoration:none;">
                <svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true" fill="currentColor">
                    <path d="M19 0H5C2.24 0 0 2.24 0 5v14c0 2.76 2.24 5 5 5h14c2.76 0 5-2.24 5-5V5c0-2.76-2.24-5-5-5ZM8 19H4V9h4v10ZM6 7.25a2.25 2.25 0 1 1 0-4.5 2.25 2.25 0 0 1 0 4.5ZM20 19h-4v-5.25c0-3.15-4-2.91-4 0V19H8V9h4v1.56c1.35-2.5 8-2.69 8 2.4V19Z"/>
                </svg> LinkedIn
            </a>
        </div>
        <div style="margin-top:14px; font-size:0.78rem; color:#64748b;">
            Made by <strong style="color:inherit;">Aman Tiwari</strong>
        </div>
        """,
        unsafe_allow_html=True,
    )

# --- HEADER SECTION ---
st.markdown(f"""
    <div style="margin-bottom: 20px;">
        <div class="gemma-brand-badge">
            <span>✦</span> Powered by Google {html_text(selected_model)} (Gemini API)
        </div>
        <h1 style="font-size: 2.2rem; font-weight: 800; margin: 0 0 6px 0;">
            Conversational Promise & Commitment Tracker
        </h1>
        <p style="font-size: 1.05rem; color: #64748b; margin: 0;">
            Find candidate commitments and unresolved questions in chat. Review model output and quote checks before relying on it.
        </p>
    </div>
""", unsafe_allow_html=True)

# --- CONVERSATION INPUT SECTION ---
with st.container():
    sample_col, sample_button_col = st.columns([4, 1])
    with sample_col:
        selected_sample = st.selectbox(
            "Try a sample conversation",
            options=list(SAMPLE_CONVERSATIONS),
            key="sample_scenario",
            help="Choose a realistic demo transcript to load into the input below.",
        )
        st.caption(SAMPLE_CONVERSATIONS[selected_sample]["description"])

    with sample_button_col:
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        if st.button("Load sample"):
            st.session_state.raw_transcript = SAMPLE_CONVERSATIONS[selected_sample]["transcript"]
            st.info("Sample loaded. The current board stays as-is until you run a new extraction.")

    transcript_input = st.text_area(
        "Paste Conversation Transcript (Slack, WhatsApp, Teams, Discord, Email, or Meeting Notes):",
        height=180,
        placeholder="[09:15 AM] Alex: Who is taking the lead on the RCA writeup?\n[09:17 AM] Priya: I will draft the RCA document and upload it to Confluence by 2:00 PM today.\n[09:18 AM] Alex: Great! Does anyone know where the AWS backup token is?\n[09:20 AM] Elena: I promise to test the cache config patch in staging before 4:00 PM.",
        help="Paste any unstructured chat log. Gemma will extract commitments, assignees, deadlines, and verbatim quotes.",
        key="raw_transcript",
        on_change=sync_persistence,
    )

    col_run, col_clear, col_info = st.columns([2, 1, 4])
    with col_run:
        if st.button("🚀 Extract Commitments with Gemma", type="primary"):
            if not transcript_input or not transcript_input.strip():
                st.warning("⚠️ Please paste a conversation transcript first.")
            else:
                with st.spinner(
                    f"Analyzing with {selected_model} (one request, up to 45 seconds)..."
                ):
                    client = GemmaClient(api_key=api_key_input, model_name=selected_model)
                    result, err = client.extract_commitments(
                        transcript=transcript_input,
                        model_override=selected_model,
                        temperature=temperature
                    )
                    if err and not result.commitments:
                        st.error(err)
                        if result.raw_response:
                            with st.expander("Inspect Gemma's raw response"):
                                st.caption(
                                    "This response can contain transcript text. It is shown only here for debugging."
                                )
                                st.code(result.raw_response, language="text")
                    else:
                        if err:
                            st.info(err)
                        st.session_state.commitments = result.commitments
                        st.session_state.unresolved_items = result.unresolved_items
                        st.session_state.extraction_result = result
                        sync_persistence()
                        st.success(f"Extracted {len(result.commitments)} commitments and {len(result.unresolved_items)} unresolved items in {result.duration_seconds}s using {result.model_used}!")
                        st.rerun()

    with col_clear:
        st.button("🗑️ Clear Board", on_click=clear_board)

# --- TOP METRICS SUMMARY ---
col_m1, col_m2, col_m3, col_m4 = st.columns(4)

total_commitments = len(st.session_state.commitments)
unresolved_count = len(st.session_state.unresolved_items)
# Calculate verified quote grounding rate
total_quotes = total_commitments + unresolved_count
verified_count = sum(1 for c in st.session_state.commitments if c.verified_in_source)
verified_count += sum(1 for item in st.session_state.unresolved_items if item.verified_in_source)
grounding_pct = f"{int((verified_count / total_quotes * 100))}%" if total_quotes > 0 else "—"
latency_str = f"{st.session_state.extraction_result.duration_seconds:.2f}s" if st.session_state.extraction_result else "-"

with col_m1:
    st.markdown(f"""
        <div class="metric-box">
            <div class="metric-number">{total_commitments}</div>
            <div class="metric-label">Buried Commitments</div>
        </div>
    """, unsafe_allow_html=True)

with col_m2:
    st.markdown(f"""
        <div class="metric-box">
            <div class="metric-number" style="color: #ea580c; -webkit-text-fill-color: #ea580c;">{unresolved_count}</div>
            <div class="metric-label">Unresolved Blockers</div>
        </div>
    """, unsafe_allow_html=True)

with col_m3:
    st.markdown(f"""
        <div class="metric-box">
            <div class="metric-number" style="color: #10b981; -webkit-text-fill-color: #10b981;">{grounding_pct}</div>
            <div class="metric-label">Source Quote Match</div>
        </div>
    """, unsafe_allow_html=True)

with col_m4:
    st.markdown(f"""
        <div class="metric-box">
            <div class="metric-number">{latency_str}</div>
            <div class="metric-label">Inference Latency</div>
        </div>
    """, unsafe_allow_html=True)

st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)
overdue_tasks = [
    task for task in st.session_state.commitments
    if task.due_date and task.due_date < date.today() and task.status != "Completed"
]
due_soon_tasks = [
    task for task in st.session_state.commitments
    if task.due_date and date.today() <= task.due_date <= date.today() + timedelta(days=7)
    and task.status != "Completed"
]
if overdue_tasks or due_soon_tasks:
    with st.expander(f"🔔 Notifications ({len(overdue_tasks) + len(due_soon_tasks)})", expanded=True):
        for task in overdue_tasks:
            st.error(
                f"**{task.id} · {task.what}** — overdue since "
                f"{task.due_date.isoformat()} · Assignee: {task.who}"
            )
        for task in due_soon_tasks:
            days_left = (task.due_date - date.today()).days
            timing = "Due today" if days_left == 0 else f"Due in {days_left} day(s)"
            st.warning(
                f"**{task.id} · {task.what}** — {timing} "
                f"({task.due_date.isoformat()}) · Assignee: {task.who}"
            )

# --- MAIN DASHBOARD TABS ---
tab_board, tab_unresolved, tab_inspector, tab_analytics, tab_export_gemma = st.tabs([
    f"📋 Commitment Board ({total_commitments})",
    f"❓ Unresolved Items ({unresolved_count})",
    "🔍 Source Quote Inspector",
    "📊 Team Workload & Analytics",
    "🤖 Gemma Integration & Export"
])

# ==========================================
# TAB 1: EDITABLE KANBAN BOARD
# ==========================================
with tab_board:
    if not st.session_state.commitments:
        st.markdown("""
            <div style="text-align: center; padding: 40px 20px; border: 2px dashed rgba(128,128,128,0.25); border-radius: 12px; margin-top: 10px;">
                <h3 style="color: #64748b; margin-bottom: 8px;">No commitments on the board yet</h3>
                <p style="color: #94a3b8; font-size: 0.95rem; max-width: 500px; margin: 0 auto 16px auto;">
                    Paste a conversation transcript in the box above and click <b>Extract Commitments with Gemma</b>, or manually add a task below.
                </p>
            </div>
        """, unsafe_allow_html=True)
    else:
        # Filter bar
        fcol1, fcol2, fcol3, fcol4 = st.columns([1.5, 1.5, 1.4, 1.6])
        with fcol1:
            all_people = ["All"] + sorted(list(set(c.who for c in st.session_state.commitments if c.who)))
            st.session_state.filter_person = st.selectbox("Filter by Assignee:", options=all_people, index=all_people.index(st.session_state.filter_person) if st.session_state.filter_person in all_people else 0)
        with fcol2:
            status_options = ["All", "To Do", "In Progress", "Blocked", "Completed"]
            st.session_state.filter_status = st.selectbox("Filter by Status:", options=status_options, index=status_options.index(st.session_state.filter_status))
        with fcol3:
            priority_filter = st.multiselect(
                "Priority",
                options=["High", "Medium", "Low"],
                default=[],
                key="filter_priority",
                placeholder="All priorities",
            )
        with fcol4:
            deadline_filter = st.selectbox(
                "Deadline",
                options=["Any date", "Overdue", "Due in 7 days", "Has due date", "No due date"],
                key="filter_deadline",
            )
        search_query = st.text_input(
            "Search the board",
            placeholder="Search IDs, tasks, people, dates, quotes, or notes...",
        )

        # Filter commitments
        filtered_commitments = st.session_state.commitments
        if st.session_state.filter_person != "All":
            filtered_commitments = [c for c in filtered_commitments if c.who == st.session_state.filter_person]
        if st.session_state.filter_status != "All":
            filtered_commitments = [c for c in filtered_commitments if c.status == st.session_state.filter_status]
        if priority_filter:
            filtered_commitments = [
                c for c in filtered_commitments if c.priority in priority_filter
            ]
        today = date.today()
        if deadline_filter == "Overdue":
            filtered_commitments = [
                c for c in filtered_commitments
                if c.due_date and c.due_date < today and c.status != "Completed"
            ]
        elif deadline_filter == "Due in 7 days":
            filtered_commitments = [
                c for c in filtered_commitments
                if c.due_date and today <= c.due_date <= today + timedelta(days=7)
                and c.status != "Completed"
            ]
        elif deadline_filter == "Has due date":
            filtered_commitments = [c for c in filtered_commitments if c.due_date]
        elif deadline_filter == "No due date":
            filtered_commitments = [c for c in filtered_commitments if not c.due_date]
        if search_query:
            q = search_query.lower()
            filtered_commitments = [
                c for c in filtered_commitments 
                if q in " ".join(
                    (
                        c.id, c.what, c.who, c.to_whom, c.by_when, c.status,
                        c.priority, c.category, c.source_quote, c.notes or "",
                        c.review_notes,
                        c.due_date.isoformat() if c.due_date else "",
                    )
                ).lower()
            ]

        # Kanban Columns Layout
        kanban_col1, kanban_col2, kanban_col3, kanban_col4 = st.columns(4)
        columns_spec = [
            ("To Do", "📝 To Do", kanban_col1, "#64748b"),
            ("In Progress", "⚡ In Progress", kanban_col2, "#2563eb"),
            ("Blocked", "⛔ Blocked", kanban_col3, "#ef4444"),
            ("Completed", "✅ Completed", kanban_col4, "#10b981"),
        ]

        for status_key, status_title, col_obj, accent_color in columns_spec:
            with col_obj:
                column_tasks = [c for c in filtered_commitments if c.status == status_key]
                st.markdown(f"""
                    <div style="display:flex; justify-content:space-between; align-items:center; border-bottom: 2px solid {accent_color}; padding-bottom: 6px; margin-bottom: 12px;">
                        <span style="font-weight:700; font-size:1.05rem;">{status_title}</span>
                        <span style="background:rgba(128,128,128,0.15); padding:2px 8px; border-radius:12px; font-size:0.8rem; font-weight:700;">{len(column_tasks)}</span>
                    </div>
                """, unsafe_allow_html=True)

                if not column_tasks:
                    st.markdown("<div style='color:#94a3b8; font-size:0.85rem; text-align:center; padding: 20px 0;'>No tasks</div>", unsafe_allow_html=True)

                for task in column_tasks:
                    safe_priority = task.priority if task.priority in {"High", "Medium", "Low"} else "Medium"
                    priority_class = f"pill-{safe_priority.lower()}"
                    verified_html = """<span class="badge-verified">✓ Quote found in source</span>""" if task.verified_in_source else """<span class="badge-unverified">~ Quote not found</span>"""

                    st.html(f"""
                        <div class="task-card">
                            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                                <span style="font-size:0.75rem; font-family:monospace; color:#64748b; font-weight:600;">{html_text(task.id)}</span>
                                <span class="pill-badge {priority_class}">{html_text(safe_priority)}</span>
                            </div>
                            <div class="task-title">{html_text(task.what)}</div>
                            <div class="task-meta">
                                <span class="pill-badge pill-assignee">👤 {html_text(task.who)}</span>
                                <span>🎯 To: <b>{html_text(task.to_whom)}</b></span>
                                <span>Review: {html_text(task.review_status)}</span>
                            </div>
                            <div style="font-size:0.82rem; color:#475569; margin-bottom:6px;">
                                ⏰ <b>Deadline:</b> <span style="background:rgba(245,158,11,0.12); color:#b45309; padding:2px 6px; border-radius:4px; font-weight:600;">{html_text(task.due_date.isoformat() if task.due_date else task.by_when)}</span>
                                {"<br/><b style='color:#dc2626;'>Overdue</b>" if task.due_date and task.due_date < date.today() and task.status != "Completed" else ""}
                                {"<br/><b style='color:#b45309;'>Due today</b>" if task.due_date == date.today() and task.status != "Completed" else ""}
                                {"<br/><b style='color:#b45309;'>Due in " + str((task.due_date - date.today()).days) + " days</b>" if task.due_date and date.today() < task.due_date <= date.today() + timedelta(days=7) and task.status != "Completed" else ""}
                            </div>
                            <div class="quote-callout">
                                "{html_text(task.source_quote)}"
                            </div>
                            <div style="display:flex; justify-content:space-between; align-items:center; margin-top:8px;">
                                {verified_html}
                                <span style="font-size:0.72rem; color:#64748b;">Model-reported: {int(task.confidence * 100)}%</span>
                            </div>
                        </div>
                    """)

                    # Action controls for this task
                    ctrl_col1, ctrl_col2 = st.columns([3, 1])
                    with ctrl_col1:
                        new_status = st.selectbox(
                            f"Move {task.id}",
                            options=["To Do", "In Progress", "Blocked", "Completed"],
                            index=["To Do", "In Progress", "Blocked", "Completed"].index(task.status),
                            key=f"status_select_{task.id}",
                            label_visibility="collapsed"
                        )
                        if new_status != task.status:
                            before = task.model_dump(mode="json")
                            task.status = new_status
                            save_task_change(task, before)
                            st.rerun()

                    with ctrl_col2:
                        if st.button("🗑️", key=f"del_{task.id}", help="Delete task"):
                            st.session_state.commitments = [c for c in st.session_state.commitments if c.id != task.id]
                            sync_persistence()
                            st.rerun()

                    with st.expander(f"Review and edit {task.id}"):
                        with st.form(f"edit_task_form_{task.id}"):
                            edit_what = st.text_input("Commitment", value=task.what)
                            edit_who = st.text_input("Assignee", value=task.who)
                            edit_to_whom = st.text_input("Recipient", value=task.to_whom)
                            edit_by_when = st.text_input("Original deadline text", value=task.by_when)
                            edit_due_date = st.date_input(
                                "Calendar due date (optional)",
                                value=task.due_date,
                                key=f"edit_due_date_{task.id}",
                            )
                            edit_priority = st.selectbox(
                                "Priority",
                                ["High", "Medium", "Low"],
                                index=["High", "Medium", "Low"].index(task.priority)
                                if task.priority in ("High", "Medium", "Low") else 1,
                                key=f"edit_priority_{task.id}",
                            )
                            edit_category = st.selectbox(
                                "Category",
                                ["Deliverable", "Review/Approval", "Bug Fix", "Logistics", "Follow-up"],
                                index=["Deliverable", "Review/Approval", "Bug Fix", "Logistics", "Follow-up"].index(task.category)
                                if task.category in ("Deliverable", "Review/Approval", "Bug Fix", "Logistics", "Follow-up") else 0,
                                key=f"edit_category_{task.id}",
                            )
                            edit_review = st.selectbox(
                                "Extraction review",
                                ["Needs review", "Correct", "Incorrect", "Corrected", "Incomplete"],
                                index=["Needs review", "Correct", "Incorrect", "Corrected", "Incomplete"].index(task.review_status)
                                if task.review_status in ("Needs review", "Correct", "Incorrect", "Corrected", "Incomplete") else 0,
                                key=f"edit_review_{task.id}",
                            )
                            edit_review_notes = st.text_area(
                                "Review notes",
                                value=task.review_notes,
                                key=f"edit_review_notes_{task.id}",
                            )
                            if st.form_submit_button("Save reviewed task"):
                                if not edit_what.strip() or not edit_who.strip():
                                    st.error("Task description and assignee are required.")
                                else:
                                    before = task.model_dump(mode="json")
                                    task.what = edit_what.strip()
                                    task.who = edit_who.strip()
                                    task.to_whom = edit_to_whom.strip() or "Team"
                                    task.by_when = edit_by_when.strip() or "Unspecified"
                                    task.due_date = edit_due_date
                                    task.priority = edit_priority
                                    task.category = edit_category
                                    task.review_status = edit_review
                                    task.review_notes = edit_review_notes.strip()
                                    save_task_change(task, before)
                                    st.success(f"Saved changes to {task.id}.")
                                    st.rerun()

    # Manual Add Task Section
    st.markdown("---")
    with st.expander("➕ Add New Commitment Manually"):
        with st.form("manual_add_task_form"):
            c1, c2, c3 = st.columns(3)
            with c1:
                new_what = st.text_input("Commitment Description *", placeholder="e.g. Prepare API integration slides")
                new_who = st.text_input("Assignee (Who promised) *", placeholder="e.g. Aman")
            with c2:
                new_to_whom = st.text_input("Recipient (To whom)", value="Team")
                new_by_when = st.text_input("Deadline (By when)", placeholder="e.g. Tomorrow 3 PM")
            with c3:
                new_status_val = st.selectbox("Status", ["To Do", "In Progress", "Blocked", "Completed"])
                new_priority_val = st.selectbox("Priority", ["High", "Medium", "Low"], index=1)

            new_quote = st.text_area("Source Quote from Chat", placeholder="Paste the sentence where this was promised")
            new_notes = st.text_input("Notes / Preconditions", placeholder="Optional context")
            new_due_date = st.date_input("Calendar due date (optional)", value=None, key="manual_due_date")

            if st.form_submit_button("Add Commitment to Board"):
                if new_what and new_who:
                    new_id = next_task_id(c.id for c in st.session_state.commitments)
                    st.session_state.commitments.append(
                        CommitmentItem(
                            id=new_id,
                            what=new_what,
                            who=new_who,
                            to_whom=new_to_whom,
                            by_when=new_by_when or "Unspecified",
                            status=new_status_val,
                            priority=new_priority_val,
                            category="Deliverable",
                            source_quote=new_quote or "Manually added commitment",
                            confidence=1.0,
                            notes=new_notes,
                            verified_in_source=bool(
                                new_quote
                                and verify_quote_in_text(
                                    new_quote, st.session_state.raw_transcript
                                )[0]
                            ),
                            due_date=new_due_date,
                            review_status="Corrected",
                        )
                    )
                    st.success(f"Added task {new_id}!")
                    sync_persistence()
                    st.rerun()
                else:
                    st.error("Please provide both task description and assignee.")

# ==========================================
# TAB 2: UNRESOLVED ITEMS & BLOCKERS
# ==========================================
with tab_unresolved:
    st.markdown("""
        <h3 style="margin-top:0;">❓ Unresolved Questions & Blockers</h3>
        <p style="color:#64748b;">
            Items discovered by Gemma where questions were asked or disputes raised without a clear commitment or answer.
        </p>
    """, unsafe_allow_html=True)

    if not st.session_state.unresolved_items:
        st.info("No unresolved questions or blockers found.")
    else:
        for idx, u in enumerate(st.session_state.unresolved_items):
            u_col1, u_col2 = st.columns([5, 2])
            with u_col1:
                st.markdown(f"""
                    <div style="background: rgba(234, 88, 12, 0.05); border: 1px solid rgba(234, 88, 12, 0.25); border-radius: 12px; padding: 16px; margin-bottom: 12px;">
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 6px;">
                            <span style="font-weight:700; font-size:1.05rem; color:#c2410c;">⚠️ {html_text(u.id)}: {html_text(u.question)}</span>
                            <span class="pill-badge pill-high">Unresolved</span>
                        </div>
                        <div style="font-size:0.85rem; color:#475569; margin-bottom:6px;">
                            🗣️ <b>Raised By:</b> {html_text(u.raised_by)} &nbsp;|&nbsp; 🚧 <b>Affecting:</b> {html_text(u.blocking)}
                        </div>
                        <div class="quote-callout-unresolved">
                            "{html_text(u.source_quote)}"
                        </div>
                    </div>
                """, unsafe_allow_html=True)

            with u_col2:
                st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
                if st.button("⚡ Convert to Action Item", key=f"conv_{u.id}"):
                    new_id = next_task_id(c.id for c in st.session_state.commitments)
                    st.session_state.commitments.append(
                        CommitmentItem(
                            id=new_id,
                            what=f"Resolve: {u.question}",
                            who=u.raised_by,
                            to_whom="Team",
                            by_when="ASAP",
                            status="To Do",
                            priority="High",
                            category="Follow-up",
                            source_quote=u.source_quote,
                            confidence=0.9,
                            notes=f"Converted from unresolved issue {u.id}. Blocking: {u.blocking}",
                            verified_in_source=u.verified_in_source
                        )
                    )
                    st.session_state.unresolved_items = [item for item in st.session_state.unresolved_items if item.id != u.id]
                    st.success(f"Converted {u.id} into action item {new_id}!")
                    sync_persistence()
                    st.rerun()

                if st.button("✅ Mark as Resolved", key=f"res_{u.id}"):
                    st.session_state.unresolved_items = [item for item in st.session_state.unresolved_items if item.id != u.id]
                    st.success(f"Resolved {u.id}!")
                    sync_persistence()
                    st.rerun()

# ==========================================
# TAB 3: SOURCE QUOTE INSPECTOR
# ==========================================
with tab_inspector:
    st.markdown("""
        <h3 style="margin-top:0;">🔍 Source Quote Checks</h3>
        <p style="color:#64748b;">
            Source quotes are highlighted when they match the transcript. A matching quote does not prove that the model interpreted it correctly or found every commitment.
        </p>
    """, unsafe_allow_html=True)

    if not st.session_state.raw_transcript:
        st.info("No conversation loaded yet. Paste a transcript above to see highlighted source quotes.")
    else:
        highlighted_html = highlight_transcript_with_quotes(
            transcript=st.session_state.raw_transcript,
            commitments=st.session_state.commitments,
            unresolved=st.session_state.unresolved_items
        )
        st.markdown(highlighted_html, unsafe_allow_html=True)

        st.markdown("---")
        st.subheader("📑 Grounding Verification Table")
        
        quote_records = []
        for c in st.session_state.commitments:
            quote_records.append({
                "Task ID": c.id,
                "Type": "Commitment",
                "Assignee": c.who,
                "Extracted Action": c.what,
                "Source Quote": c.source_quote,
                "Status": "✅ Quote found in transcript" if c.verified_in_source else "⚠️ Quote not found",
                "Model-reported confidence": f"{int(c.confidence * 100)}%"
            })
        for u in st.session_state.unresolved_items:
            quote_records.append({
                "Task ID": u.id,
                "Type": "Unresolved Issue",
                "Assignee": u.raised_by,
                "Extracted Action": u.question,
                "Source Quote": u.source_quote,
                "Status": "✅ Quote found in transcript" if u.verified_in_source else "⚠️ Quote not found",
                "Confidence": "N/A"
            })

        if quote_records:
            st.dataframe(quote_records)

# ==========================================
# TAB 4: TEAM WORKLOAD & ANALYTICS
# ==========================================
with tab_analytics:
    st.markdown("<h3 style='margin-top:0;'>📊 Accountability & Workload Distribution</h3>", unsafe_allow_html=True)

    if not st.session_state.commitments:
        st.info("No commitment data available to analyze. Extract commitments to view team workload.")
    else:
        an_col1, an_col2 = st.columns(2)
        with an_col1:
            st.subheader("👤 Commitments per Person")
            who_counts = {}
            for c in st.session_state.commitments:
                who_counts[c.who] = who_counts.get(c.who, 0) + 1
            st.bar_chart(who_counts)

        with an_col2:
            st.subheader("🏷️ Tasks by Category")
            cat_counts = {}
            for c in st.session_state.commitments:
                cat_counts[c.category] = cat_counts.get(c.category, 0) + 1
            st.bar_chart(cat_counts)

        st.subheader("⚡ Commitment Urgency Breakdown")
        u_col1, u_col2, u_col3 = st.columns(3)
        with u_col1:
            high_count = sum(1 for c in st.session_state.commitments if c.priority == "High")
            st.metric("High Priority Commitments", high_count)
        with u_col2:
            med_count = sum(1 for c in st.session_state.commitments if c.priority == "Medium")
            st.metric("Medium Priority", med_count)
        with u_col3:
            low_count = sum(1 for c in st.session_state.commitments if c.priority == "Low")
            st.metric("Low Priority", low_count)

# ==========================================
# TAB 5: GEMMA INTEGRATION & EXPORT
# ==========================================
with tab_export_gemma:
    st.markdown(f"""
        <div style="background: rgba(66, 133, 244, 0.06); border: 1px solid rgba(66, 133, 244, 0.2); border-radius: 12px; padding: 18px; margin-bottom: 20px;">
            <h3 style="margin-top:0; color:#1a73e8;">🤖 Google Gemma 4 Model Architecture & Gemini API Integration</h3>
            <p>
                <b>Promise Tracker</b> integrates Google's latest <b>Gemma 4</b> generation (e.g. <code>{html_text(selected_model)}</code>) via the official <code>google-genai</code> SDK.
            </p>
            <ul>
                <li><b>Model Family:</b> Google Gemma 4.</li>
                <li><b>Endpoint:</b> <code>models/{html_text(selected_model)}</code> via Google Gemini API.</li>
                <li><b>Prompt Engineering:</b> Requests structured commitment data and source quotes, then validates returned quotes against the supplied transcript.</li>
                <li><b>Review:</b> AI output is a suggestion. Verify the owner, action, deadline, and surrounding context before acting.</li>
            </ul>
        </div>
    """, unsafe_allow_html=True)

    # Export Buttons
    st.subheader("📥 Export Action Items")
    if not st.session_state.commitments and not st.session_state.unresolved_items:
        st.info("No action items to export yet.")
    else:
        exp_col1, exp_col2, exp_col3 = st.columns(3)

        csv_data = export_commitments_to_csv(st.session_state.commitments, st.session_state.unresolved_items)
        md_data = export_commitments_to_markdown(st.session_state.commitments, st.session_state.unresolved_items)
        json_data = json.dumps({
            "commitments": [c.model_dump(mode="json") for c in st.session_state.commitments],
            "unresolved_items": [u.model_dump(mode="json") for u in st.session_state.unresolved_items]
        }, indent=2)

        with exp_col1:
            st.download_button(
                "📄 Download CSV (Excel / Sheets)",
                data=csv_data,
                file_name="commitments_promise_tracker.csv",
                mime="text/csv"
            )

        with exp_col2:
            st.download_button(
                "📋 Download Markdown (GitHub / Notion)",
                data=md_data,
                file_name="commitments_promise_tracker.md",
                mime="text/markdown"
            )

        with exp_col3:
            st.download_button(
                "⚙️ Download JSON",
                data=json_data,
                file_name="commitments_promise_tracker.json",
                mime="application/json"
            )

    st.markdown("---")
    with st.expander("🛠️ View Gemma System Prompt"):
        st.code(GEMMA_SYSTEM_PROMPT, language="markdown")

    with st.expander("📦 View Raw Extraction Response JSON"):
        if st.session_state.extraction_result and st.session_state.extraction_result.raw_response:
            st.code(st.session_state.extraction_result.raw_response, language="json")
        else:
            st.write("No extraction response loaded yet.")
