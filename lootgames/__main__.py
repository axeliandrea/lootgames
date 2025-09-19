ubuntu@ubuntu:~/lootgames$ python3 -m lootgames
Traceback (most recent call last):
  File "/usr/lib/python3.10/runpy.py", line 196, in _run_module_as_main
    return _run_code(code, main_globals, None,
  File "/usr/lib/python3.10/runpy.py", line 86, in _run_code
    exec(code, run_globals)
  File "/home/ubuntu/lootgames/lootgames/__main__.py", line 32, in <module>
    @app.on_ready  # pyrogram >=2.0
AttributeError: 'Client' object has no attribute 'on_ready'
ubuntu@ubuntu:~/lootgames$ 
