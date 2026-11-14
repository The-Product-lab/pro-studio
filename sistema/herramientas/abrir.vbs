' Abre la app SIN ventana de terminal (lo que llama el acceso directo del escritorio en Windows).
Set sh = CreateObject("WScript.Shell")
carpeta = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
sh.CurrentDirectory = carpeta & "\.."
' Python en modo UTF-8 (los textos del sistema llevan acentos; en Windows el valor por defecto es cp1252)
sh.Environment("PROCESS")("PYTHONUTF8") = "1"
sh.Environment("PROCESS")("PYTHONIOENCODING") = "utf-8"
sh.Run "cmd /c abrir.bat", 0, False
