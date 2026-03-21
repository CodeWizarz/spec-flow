import logging
import datetime
from celery import shared_task
from plane.signals.models import Signal, Insight, GeneratedSpec
from django.conf import settings
import json
try:
    import openai
except ImportError:
    openai = None

logger = logging.getLogger(__name__)

@shared_task
def process_signal_file_task(signal_id):
    try:
        signal = Signal.objects.get(id=signal_id)
        if signal.file:
            # Placeholder text extraction logic for M1
            extracted_text = f"\\n\\n[Extracted from {signal.file.name}]\\nFeedback looks valid."
            
            signal.content = (signal.content or "") + extracted_text
            signal.processing_status = "processed"
            signal.save()
            logger.info(f"Successfully processed signal {signal_id}")
            
    except Signal.DoesNotExist:
        logger.error(f"Signal {signal_id} not found.")
    except Exception as e:
        logger.error(f"Error processing signal {signal_id}: {str(e)}")
        try:
            signal = Signal.objects.get(id=signal_id)
            signal.processing_status = "error"
            signal.save()
        except:
            pass

@shared_task
def generate_insights_task(workspace_id):
    signals = Signal.objects.filter(workspace_id=workspace_id, processing_status="processed")
    if not signals.exists() or openai is None:
        logger.warning(f"No processed signals found for workspace {workspace_id} or openai not installed.")
        return

    combined_text = "\\n\\n---\\n\\n".join([f"Signal: {s.title}\\n{s.content}" for s in signals])
    
    system_prompt = (
        "You are an expert product manager analyzing unstructured customer feedback. "
        "Extract recurring actionable themes and core problems. "
        "Respond STRICTLY in JSON format. The response must be a JSON object containing a 'data' array. "
        "Each object in the 'data' array MUST have these exact keys: 'theme', 'problem', 'root_cause', 'evidence', and 'frequency'. "
        "'evidence' must be an array of strings directly quoting the user feedback. 'frequency' should be an integer count of occurrences. "
        "Do not include any free text outside the JSON."
    )

    try:
        client = openai.OpenAI(api_key=getattr(settings, "OPENAI_API_KEY", ""))
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": combined_text}
            ],
            temperature=0.0,
            response_format={"type": "json_object"}
        )
        
        response_json = json.loads(response.choices[0].message.content)
        insights_data = response_json.get("data", [])
        
        for item in insights_data:
            Insight.objects.create(
                workspace_id=workspace_id,
                theme=item.get("theme", "Unknown Theme"),
                problem=item.get("problem", "Unknown Problem"),
                root_cause=item.get("root_cause", ""),
                evidence=item.get("evidence", []),
                frequency=item.get("frequency", 1)
            )
            
        signals.update(processing_status="insight_generated")
        logger.info(f"Successfully generated insights for workspace {workspace_id}")
        
    except Exception as e:
        logger.error(f"Error generating insights for workspace {workspace_id}: {str(e)}")

@shared_task
def generate_spec_task(workspace_id, insight_ids=None):
    if insight_ids:
        insights = Insight.objects.filter(id__in=insight_ids, workspace_id=workspace_id)
    else:
        insights = Insight.objects.filter(workspace_id=workspace_id).order_by('-created_at')[:20]
        
    if not insights.exists() or openai is None:
        logger.warning(f"No insights found for workspace {workspace_id} or openai not installed.")
        return

    combined_text = "\\n\\n---\\n\\n".join([
        f"Theme: {i.theme}\\nProblem: {i.problem}\\nRoot Cause: {i.root_cause}\\nFrequency: {i.frequency}"
        for i in insights
    ])
    
    system_prompt = (
        "You are an expert autonomous software architect. "
        "Convert the following recurring customer problems into a strict, concise, and structured JSON software specification. "
        "STRICT CONCISENESS RULES: Fields must be short and actionable. Do NOT use long paragraphs. "
        "Respond STRICTLY in JSON format with a parent key `data` containing an object with the following keys: "
        "- `feature_name` (string): Short descriptive title. "
        "- `problem` (string): Condensed summary of what to solve. "
        "- `user_story` (string): As a [user], I want to [action] so that [benefit]. "
        "- `solution` (string): Concise description of the fix. "
        "- `ui_changes` (array of strings): Bullet-style UI updates. "
        "- `data_model_changes` (array of strings): Bullet-style DB changes. "
        "- `workflow_changes` (array of strings): Bullet-style API/flow changes. "
        "- `tasks` (array of objects): MUST contain exact keys `read_first` (array of filenames) and `action` (array of short bullet-style instructions)."
    )

    try:
        client = openai.OpenAI(api_key=getattr(settings, "OPENAI_API_KEY", ""))
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": combined_text}
            ],
            temperature=0.0,
            response_format={"type": "json_object"}
        )
        
        response_json = json.loads(response.choices[0].message.content)
        spec_data = response_json.get("data", {})
        
        GeneratedSpec.objects.create(
            workspace_id=workspace_id,
            title=spec_data.get("feature_name", f"Spec generated {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}"),
            spec_json=spec_data
        )
        logger.info(f"Successfully generated spec for workspace {workspace_id}")
        
    except Exception as e:
        logger.error(f"Error generating spec for workspace {workspace_id}: {str(e)}")
