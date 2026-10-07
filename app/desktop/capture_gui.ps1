$edge='C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
$out='D:\Projects\ExamPPT\app\desktop\gui_v0_1.png'
& $edge --headless=new --disable-gpu --hide-scrollbars --window-size=1440,900 --screenshot=$out 'http://127.0.0.1:1420/'
