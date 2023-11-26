"""
Minimal GUI for Assistant
"""
import threading
import PySimpleGUI as sg
from assistant import *

OUTPUT = '-OUT-'+sg.WRITE_ONLY_KEY

sg.theme('Dark Blue 3')
sg.Print('STDOUT logged here', do_not_reroute_stdout=False)  # Routes stdout to a "debug" window
layout = [[sg.MLine(key='Input', size=(60,2), enter_submits=True), sg.Text("<< Message the Assistant"), sg.Button('Submit', bind_return_key=True)],
          [sg.MLine(key=OUTPUT, size=(120, 30), autoscroll=True, write_only=True, disabled=True)]]

def main():
    window = sg.Window('Assistant Demo', layout)

    AI = Assistant()

    while True:  # Event Loop
        event, values = window.read()
        print('\n', event, values)
        if event == sg.WIN_CLOSED or event == 'Exit':
            break
        if event == 'Submit' or event == "Input_Enter":
            message = values['Input']
            window[OUTPUT].print('Sending:\n\t' + message, c='blue')
            window['Input'].Update('')  # Clear the input text
            threading.Thread(target=AI.send_message, args=(window, message), daemon=True).start()
        if event == AI_RESPONSE:
            window[OUTPUT].print('\n[Received response:]', c='red')
            for m in values[AI_RESPONSE]:
                window[OUTPUT].print(f"{m.role}: {m.content[0].text.value}")
            window[OUTPUT].print('[End response.]', c='red')

    window.close()

if __name__ == '__main__':
    main()
