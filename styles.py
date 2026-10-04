"""
Custom modern CSS styling for Promise Tracker Streamlit Application.
Provides sleek card designs, pill badges, and quote callouts for both light and dark modes.
"""

CUSTOM_CSS = """
<style>
/* Global polish */
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

html, body, [class*="css"] {
    font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
}

/* Header badge styling */
.gemma-brand-badge {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: linear-gradient(135deg, rgba(66, 133, 244, 0.15) 0%, rgba(219, 68, 85, 0.15) 100%);
    border: 1px solid rgba(66, 133, 244, 0.3);
    padding: 6px 14px;
    border-radius: 9999px;
    font-size: 0.85rem;
    font-weight: 600;
    color: #4285F4;
    margin-bottom: 8px;
}

/* Metric card styling */
.metric-box {
    background: rgba(128, 128, 128, 0.05);
    border: 1px solid rgba(128, 128, 128, 0.15);
    border-radius: 12px;
    padding: 16px;
    text-align: center;
    box-shadow: 0 2px 6px rgba(0,0,0,0.02);
}
.metric-number {
    font-size: 2rem;
    font-weight: 800;
    line-height: 1.1;
    background: linear-gradient(135deg, #4285F4 0%, #34A853 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
.metric-label {
    font-size: 0.8rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #64748b;
    font-weight: 600;
    margin-top: 4px;
}

/* Kanban Task Card styling */
.task-card {
    background: rgba(128, 128, 128, 0.04);
    border: 1px solid rgba(128, 128, 128, 0.18);
    border-radius: 12px;
    padding: 14px;
    margin-bottom: 12px;
    transition: all 0.2s ease-in-out;
}
.task-card:hover {
    border-color: #4285F4;
    box-shadow: 0 4px 12px rgba(66, 133, 244, 0.08);
}
.task-title {
    font-size: 1rem;
    font-weight: 700;
    margin-bottom: 6px;
}
.task-meta {
    font-size: 0.82rem;
    color: #64748b;
    margin-bottom: 8px;
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    align-items: center;
}

/* Quote Callout Box */
.quote-callout {
    background: rgba(66, 133, 244, 0.07);
    border-left: 3px solid #4285F4;
    border-radius: 4px;
    padding: 6px 10px;
    font-size: 0.82rem;
    font-style: italic;
    color: #334155;
    margin-top: 8px;
    margin-bottom: 6px;
}
.quote-callout-unresolved {
    background: rgba(234, 88, 12, 0.08);
    border-left: 3px solid #ea580c;
    border-radius: 4px;
    padding: 6px 10px;
    font-size: 0.82rem;
    font-style: italic;
    color: #9a3412;
    margin-top: 8px;
}

/* Badges and Pills */
.pill-badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 9999px;
    font-size: 0.75rem;
    font-weight: 600;
}
.pill-high { background-color: rgba(239, 68, 68, 0.15); color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.3); }
.pill-medium { background-color: rgba(245, 158, 11, 0.15); color: #f59e0b; border: 1px solid rgba(245, 158, 11, 0.3); }
.pill-low { background-color: rgba(59, 130, 246, 0.15); color: #3b82f6; border: 1px solid rgba(59, 130, 246, 0.3); }

.pill-todo { background-color: rgba(100, 116, 139, 0.15); color: #64748b; }
.pill-progress { background-color: rgba(59, 130, 246, 0.15); color: #3b82f6; }
.pill-blocked { background-color: rgba(239, 68, 68, 0.15); color: #ef4444; }
.pill-completed { background-color: rgba(16, 185, 129, 0.15); color: #10b981; }

.pill-assignee {
    background: rgba(66, 133, 244, 0.1);
    color: #2563eb;
    font-weight: 600;
}

/* Grounding verification badge */
.badge-verified {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    color: #10b981;
    font-size: 0.75rem;
    font-weight: 600;
}
.badge-unverified {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    color: #f59e0b;
    font-size: 0.75rem;
    font-weight: 600;
}
@media (max-width: 768px) {
    .block-container {
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }
    .gemma-brand-badge {
        max-width: 100%;
        white-space: normal;
        overflow-wrap: anywhere;
    }
    .metric-box {
        padding: 12px 8px;
    }
    .metric-number {
        font-size: 1.6rem;
    }
    .metric-label {
        font-size: 0.68rem;
        letter-spacing: 0.03em;
    }
    .task-card,
    .quote-callout,
    .quote-callout-unresolved {
        overflow-wrap: anywhere;
        word-break: break-word;
    }
    .task-card {
        padding: 11px;
    }
    .task-meta {
        align-items: flex-start;
    }
    div[data-baseweb="tab-list"] {
        flex-wrap: wrap;
        gap: 0.25rem;
    }
}</style>
"""
