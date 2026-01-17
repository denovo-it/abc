# Copyright Axelera AI, 2025
"""
ui.py
Reusable Gradio UI builder for LLM chat, with a Axelera-Customized and a native UI.
"""
import importlib.metadata
import os
from pathlib import Path
import site

from axelera.llm import config, logging_utils

LOG = logging_utils.getLogger(__name__)

GRADIO_AVAILABLE = False
try:
    import gradio as gr

    GRADIO_AVAILABLE = True
except ImportError:
    LOG.warning("Gradio not available! Please install it to use the UI features.")

from .conversation import stream_response


def _create_chat_logic(
    keep_history,
    model_instance,
    chat_encoder,
    tokenizer,
    max_tokens,
    temperature,
    end_token_id,
    error_status_message="Error",
    tracers=None,
):
    """Helper function to create chat logic (chat_fn and clear_history)."""

    def chat_fn(message, history):
        import time

        if history is None:
            history = []

        chat_history = [] if not keep_history else [(h[0], h[1]) for h in history if h[0] and h[1]]

        history = history + [[message, ""]]
        yield history, "", "Ready"

        try:
            input_ids, embedding_features = chat_encoder.encode(message, chat_history)
            response = ""
            for new_text, stats in stream_response(
                model_instance,
                chat_encoder,
                tokenizer,
                input_ids,
                embedding_features,
                max_tokens,
                temperature,
                tokenizer.eos_token_id,
                end_token_id,
                tracers=tracers,
            ):
                response = new_text
                history[-1][1] = response
                status_str = f"TTFT: {stats['ttft']:.2f}s | Tokens/sec: {stats['tokens_per_sec']:.2f} | Tokens: {stats['tokens']}"

                if tracers:
                    status_str += format_system_metrics(tracers)
                yield history, "", status_str

            chat_encoder.add_to_history(message, response)
            LOG.info(f"User message processed, response length: {len(response)}")

            if not keep_history:
                LOG.debug(
                    "--history flag not enabled, clearing conversation history after response"
                )
                chat_encoder.reset(preserve_system_prompt=True)
        except Exception as e:
            LOG.error(f"Error processing message: {str(e)}")
            error_message = f"Sorry, an error occurred: {str(e)}"
            history[-1][1] = error_message
            yield history, "", error_status_message

    def clear_history():
        chat_encoder.reset(preserve_system_prompt=True)
        LOG.info("Chat history cleared.")
        return [], "", "Ready"

    return chat_fn, clear_history


def asset_path(name: str) -> str:
    asset_rel_path = os.path.join("assets", "file")
    prefix = Path(__file__).resolve().parent

    asset_path = Path(os.path.join(prefix, asset_rel_path))
    full_path = asset_path / name
    if full_path.exists():
        return str(full_path)

    LOG.error(f"Asset file not found: {full_path}")
    raise FileNotFoundError(f"Asset file not found: {full_path}")


def load_css():
    css_rel_path = os.path.join("assets", "styles.css")
    prefix = Path(__file__).resolve().parent

    css_path = Path(os.path.join(prefix, css_rel_path))
    if css_path.exists():
        with open(css_path, 'r') as f:
            return f.read()

    LOG.error(f"CSS file not found: {css_path}")
    raise FileNotFoundError(f"CSS file not found: {css_path}")


def format_system_metrics(tracers):
    """
    Format system metrics from tracers into a string for display.

    Args:
        tracers: List of tracer objects

    Returns:
        String representation of metrics or empty string if no tracers
    """
    if not tracers:
        return ""

    system_metrics = []
    for tracer in tracers:
        for metric in tracer.get_metrics():
            system_metrics.append(f"{metric.title}: {metric.value:.1f}{metric.unit}")

    if system_metrics:
        return " | " + " | ".join(system_metrics)
    return ""


def create_header_html():
    # Use the merged logo if you demo on Arduinio platform
    logo_path = asset_path("Axelera-AI-logo-White.png")
    icon_path = asset_path("AX-TOP-Icon-.png")
    with gr.Row(elem_classes="header-container") as header:
        with gr.Column(elem_classes="logo-wrapper"):
            gr.Image(
                logo_path,
                container=False,
                show_label=False,
                elem_classes=["logo"],
                interactive=False,
                show_download_button=False,
                show_fullscreen_button=False,
            )
        with gr.Row(elem_classes="title-container"):
            gr.Image(
                icon_path,
                container=False,
                show_label=False,
                elem_classes=["icon"],
                interactive=False,
                show_download_button=False,
                show_fullscreen_button=False,
            )
            gr.Markdown(
                """
                <div class="title-text">
                    <p class="axelera">Axelera AI</p>
                    <p class="slm-demo">SLM Demo</p>
                </div>
                """
            )
    return header


def get_short_model_name(model_name):
    """Return the short model name for display, handling both with and without '/' in the name."""
    if model_name is not None:
        if "/" in model_name:
            return model_name.split("/")[-1]
        else:
            return model_name
    return "Unknown Model"


def _build_chat_interface(current_system_prompt):
    """Builds the chat interface elements."""
    with gr.Column(elem_classes="chatbox"):
        chatbot = gr.Chatbot(
            show_label=False,
            elem_classes="chat-display",
            avatar_images=(None, asset_path("AX-TOP-Icon-.png")),
            resizeable=True,
        )
        with gr.Row(elem_classes="input-container"):
            msg = gr.Textbox(
                show_label=False,
                placeholder="Ask me something...",
                container=False,
                elem_classes="message-input",
                scale=9,
                submit_btn='➤',
            )
            clear = gr.ClearButton(value="Clear", scale=1, elem_classes="clear-btn")
    return chatbot, msg, clear


def _build_system_prompt_modal(current_system_prompt, chat_encoder):
    """Builds the system prompt modal and its interactions."""
    system_prompt_state = gr.State(current_system_prompt)
    with gr.Group(visible=False) as modal_group:
        gr.Markdown("### System Prompt Settings")
        system_prompt_input = gr.Textbox(
            label="", value=current_system_prompt, lines=5, elem_classes="system-prompt-input"
        )
        with gr.Row():
            update_prompt_btn = gr.Button("Update", elem_classes="update-prompt-btn")
            cancel_btn = gr.Button("Cancel", elem_classes="cancel-btn")

    def show_modal(current_prompt_val):
        return gr.Group(visible=True), gr.update(value=current_prompt_val)

    def hide_modal():
        return gr.Group(visible=False), gr.update()

    def update_prompt(new_prompt):
        chat_encoder.update_system_prompt(new_prompt)
        LOG.info(f"System prompt updated: {new_prompt}")
        return gr.Group(visible=False), new_prompt

    return (
        modal_group,
        system_prompt_input,
        update_prompt_btn,
        cancel_btn,
        system_prompt_state,
        show_modal,
        hide_modal,
        update_prompt,
    )


def _build_settings_and_status_bar():
    """Builds the settings button and status bar."""
    with gr.Row(elem_classes="status-container"):
        with gr.Column(scale=1, min_width=45):
            settings_btn = gr.Button(
                value="",
                icon=asset_path("setting.png"),
                elem_classes="settings-btn",
            )
        with gr.Column(scale=5):
            pass  # Placeholder for status messages if needed
        with gr.Column(scale=4):
            pass  # Placeholder for system info if needed
    status = gr.Markdown(value="Ready", elem_classes="status-text")
    return settings_btn, status


def _get_auto_scroll_js(selector='.chat-display'):
    """Returns JavaScript code for auto-scrolling chat windows.
    Typically, Gradio has this feature built-in adn defaults to true.
    However, it sometimes fails to work, so we add this as a workaround.

    Args:
        selector: The CSS selector to find the chat container elements.

    Returns:
        JavaScript code as a string for attaching auto-scroll behavior.
    """
    return f"""
function setupAutoScroll() {{
    const chatContainers = document.querySelectorAll('{selector}');
    if (chatContainers && chatContainers.length > 0) {{
        chatContainers.forEach(container => {{
            const observer = new MutationObserver(() => {{
                container.scrollTop = container.scrollHeight;
            }});

            observer.observe(container, {{
                childList: true,
                subtree: true,
                characterData: true
            }});
        }});
        console.log('Auto-scroll enabled for {selector}');
    }} else {{
        setTimeout(setupAutoScroll, 100);
    }}
}}
setupAutoScroll();
"""


def _get_esc_key_handler_js():
    """Returns JavaScript code for ESC key handling to clear chat history.

    Returns:
        JavaScript code as a string for handling ESC key press.
    """
    return """
// ESC key to clear chat history
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        const clearBtn = document.querySelector('button.clear-btn');
        if (clearBtn) clearBtn.click();
    }
});
"""


def build_llm_ui(
    model_instance,
    chat_encoder,
    tokenizer,
    max_tokens,
    system_prompt,
    temperature,
    model_name,
    end_token_id,
    keep_history=True,
    tracers=None,
):
    """
    Build a Gradio Blocks UI for LLM chat, matching phi3_demo.py.
    Returns a Gradio Blocks app.
    """

    # chat_encoder.system_prompt is the source of truth.
    # system_prompt param is used for initial UI state.
    current_system_prompt = chat_encoder.system_prompt

    css = load_css()
    LOG.info("Building LLM Gradio UI...")

    # Extract short model name for display
    short_model_name = get_short_model_name(model_name)

    chat_fn, clear_history = _create_chat_logic(
        keep_history,
        model_instance,
        chat_encoder,
        tokenizer,
        max_tokens,
        temperature,
        end_token_id,
        error_status_message="Error",  # Specific for this UI
        tracers=tracers,
    )

    with gr.Blocks(
        theme=gr.themes.Soft(primary_hue="blue", secondary_hue="gray").set(
            body_background_fill="linear-gradient(180deg, #000000 0%, #0A1130 50%, #152147 100%), radial-gradient(circle at top right, #000000, transparent)",
            body_background_fill_dark="linear-gradient(180deg, #000000 0%, #0A1130 50%, #152147 100%), radial-gradient(circle at top right, #000000, transparent)",
            background_fill_primary="#0D1223",
            background_fill_primary_dark="#0D1223",
            background_fill_secondary="rgba(13, 18, 35, 0.95)",
            background_fill_secondary_dark="rgba(13, 18, 35, 0.95)",
            body_text_color="white",
            body_text_color_dark="white",
            body_text_color_subdued='*secondary_200',
            body_text_color_subdued_dark='*secondary_200',
            border_color_primary="rgba(180, 180, 180, 0.1)",
            border_color_primary_dark="rgba(180, 180, 180, 0.1)",
            panel_background_fill="#0D1223",
            panel_background_fill_dark="#0D1223",
            block_background_fill="#050918",
            block_label_background_fill="#050918",
            input_background_fill="#050918",
            button_secondary_background_fill="#050918",
            input_border_color="rgba(180, 180, 180, 0.2)",
        ),
        css=css,
    ) as demo:
        header = create_header_html()
        gr.Markdown(
            f'<div class="chat-header"><b>Chat with the <span style="color:#FBBE18">{short_model_name}</span> model.<br>Enter your message and see the AI respond in real-time.</b></div>'
        )

        chatbot, msg, clear = _build_chat_interface(current_system_prompt)

        (
            modal_group,
            system_prompt_input,
            update_prompt_btn,
            cancel_btn,
            system_prompt_state,
            show_modal_fn,
            hide_modal_fn,
            update_prompt_fn,
        ) = _build_system_prompt_modal(current_system_prompt, chat_encoder)

        settings_btn, status = _build_settings_and_status_bar()

        msg.submit(chat_fn, [msg, chatbot], [chatbot, msg, status], queue=True, api_name="chat")
        clear.click(clear_history, None, [chatbot, msg, status], queue=False)

        update_prompt_btn.click(
            fn=update_prompt_fn,
            inputs=[system_prompt_input],
            outputs=[modal_group, system_prompt_state],
        )
        cancel_btn.click(fn=hide_modal_fn, outputs=[modal_group, system_prompt_input])
        settings_btn.click(
            fn=show_modal_fn,
            inputs=[system_prompt_state],
            outputs=[modal_group, system_prompt_input],
        )

        # Add keyboard shortcuts and auto-scroll functionality
        demo.load(
            fn=None,
            inputs=None,
            outputs=None,
            js=f"""() => {{
                {_get_esc_key_handler_js()}
                {_get_auto_scroll_js('.chat-display')}
            }}""",
        )
    return demo


def build_llm_ui_native(
    model_instance,
    chat_encoder,
    tokenizer,
    max_tokens,
    system_prompt,
    temperature,
    model_name=None,
    end_token_id=None,
    keep_history=True,
    tracers=None,
):
    """
    Build a modern, native Gradio UI for LLM chat using only Gradio's built-in themes and components.
    This version supports temperature adjustment.

    Returns a Gradio Blocks app.
    """
    current_system_prompt = chat_encoder.system_prompt
    LOG.info("Building native Gradio LLM UI...")
    short_model_name = get_short_model_name(model_name)

    temperature_value = [temperature]

    def temp_aware_chat_fn(message, history):
        current_temp = temperature_value[0]
        if history is None:
            history = []

        chat_history = [] if not keep_history else [(h[0], h[1]) for h in history if h[0] and h[1]]
        history = history + [[message, ""]]
        yield history, "", "Ready"

        try:
            input_ids, embedding_features = chat_encoder.encode(message, chat_history)
            response = ""
            for new_text, stats in stream_response(
                model_instance,
                chat_encoder,
                tokenizer,
                input_ids,
                embedding_features,
                max_tokens,
                current_temp,
                tokenizer.eos_token_id,
                end_token_id,
                tracers=tracers,
            ):
                response = new_text
                history[-1][1] = response
                status_str = f"TTFT: {stats['ttft']:.2f}s | Tokens/sec: {stats['tokens_per_sec']:.2f} | Tokens: {stats['tokens']}"

                if tracers:
                    status_str += format_system_metrics(tracers)

                yield history, "", status_str

            chat_encoder.add_to_history(message, response)
            LOG.info(f"User message processed, response length: {len(response)}")

            if not keep_history:
                LOG.debug(
                    "--history flag not enabled, clearing conversation history after response"
                )
                chat_encoder.reset(preserve_system_prompt=True)
        except Exception as e:
            LOG.error(f"Error processing message: {str(e)}")
            error_message = f"Sorry, an error occurred: {str(e)}"
            history[-1][1] = error_message
            yield history, "", "Error"

    def clear_history():
        chat_encoder.reset(preserve_system_prompt=True)
        LOG.info("Chat history cleared.")
        return [], "", "Ready"

    with gr.Blocks(
        theme=gr.themes.Soft(
            primary_hue="indigo",
            secondary_hue="blue",
            neutral_hue="slate",
            radius_size="lg",
            font=(gr.themes.GoogleFont("Inter"), gr.themes.GoogleFont("IBM Plex Mono")),
        )
    ) as demo:
        with gr.Row(equal_height=True):
            with gr.Column(scale=1, min_width=60):
                gr.Image(
                    asset_path("Axelera-AI-logo-White.png"),
                    show_label=False,
                    height=40,
                    container=False,
                    interactive=False,
                    show_download_button=False,
                    show_fullscreen_button=False,
                )
            with gr.Column(scale=5):
                gr.Markdown(f"# SLM Demo\n### Chat with {short_model_name} on Metis")

        with gr.Group(visible=True):
            chatbot = gr.Chatbot(
                value=[],
                height=450,
                show_label=False,
                avatar_images=(None, asset_path("AX-TOP-Icon-.png")),
                bubble_full_width=False,
                autoscroll=True,
            )

        with gr.Row():
            msg = gr.Textbox(
                placeholder="Type your message...",
                show_label=False,
                scale=9,
                autofocus=True,
                container=True,
                lines=1,
                submit_btn="➤",
            )
            clear = gr.ClearButton(value="Clear", size="sm", scale=1)

        with gr.Row():
            status = gr.Markdown("**Status:** Ready", elem_id="status-bar")

        with gr.Accordion("Settings", open=False):
            with gr.Row():
                with gr.Column(scale=3):
                    system_prompt_box = gr.Textbox(
                        label="System Prompt",
                        value=current_system_prompt,
                        lines=3,
                        max_lines=5,
                    )
                with gr.Column(scale=1):
                    temp_slider = gr.Slider(
                        label="Temperature",
                        minimum=0,
                        maximum=1.5,
                        value=temperature,
                        step=0.05,
                    )

            def update_system_prompt(new_prompt):
                chat_encoder.update_system_prompt(new_prompt)

            def update_temperature(new_temp):
                temperature_value[0] = new_temp
                LOG.info(f"Temperature updated to {new_temp}")

            system_prompt_box.change(update_system_prompt, inputs=[system_prompt_box])
            temp_slider.change(update_temperature, inputs=[temp_slider])

        msg.submit(temp_aware_chat_fn, [msg, chatbot], [chatbot, msg, status], queue=True)
        clear.click(clear_history, None, [chatbot, msg, status], queue=False)

        # Add ESC key handler
        demo.load(
            fn=None, inputs=None, outputs=None, js=f"""() => {{ {_get_esc_key_handler_js()} }}"""
        )

    return demo
