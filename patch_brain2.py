import re
filepath = r'd:\Projects\Ai_Assistant\core_ai\src\ai_assistant\core\command_brain.py'
with open(filepath, 'r', encoding='utf-8') as f:
    text = f.read()

injection = '''        # We need a background task so it doesn't block the API
        def run_coordinator():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(coordinator.process_command(command))
                loop.close()
                
                # Emit result back to UI
                try:
                    import sys
                    from datetime import datetime
                    
                    if 'backend.voice_service' in sys.modules:
                        from backend.voice_service import safe_emit
                        
                        msg = result.get('message', '')
                        if result.get('status') == 'success':
                            msg = f"Task Completed: {msg}"
                        
                        safe_emit('command_response', {
                            'success': result.get('status') != 'error',
                            'response': msg,
                            'command': command,
                            'source': 'local_gguf_agent',
                            'timestamp': datetime.now().isoformat(),
                            'skip_tts': False
                        })
                except Exception as emit_e:
                    import logging
                    logging.getLogger(__name__).error(f"Failed to emit coordinator result: {emit_e}")
                    
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Coordinator failed: {e}")
                
        threading.Thread(target=run_coordinator, daemon=True).start()'''

pattern = re.compile(r'        # We need a background task so it doesn\'t block the API.*?        threading\.Thread\(target=run_coordinator, daemon=True\)\.start\(\)', re.DOTALL)

if pattern.search(text):
    new_text = pattern.sub(injection.strip(), text)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_text)
    print('Patched successfully!')
else:
    print('Could not find the target block to patch.')
