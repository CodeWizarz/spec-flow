import logging
from celery import shared_task
from plane.signals.models import Signal

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
