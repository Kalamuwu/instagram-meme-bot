// webserver/websocket.js
// sets up and manages the websocket.

const protocol = (location.protocol==="http:") ? 'ws' : 'wss';
const url = `${protocol}://${location.host}/ws/app/`;
const ws = new ReconnectingWebSocket(url, null, {debug: true, reconnectInterval: 3000});

function add_log_entry(msg) {
    const logDiv = document.getElementById("log");
    logDiv.insertAdjacentHTML('beforeend', `<div class="logentry"> <span> ${msg} </span> </div>`);
    logDiv.scrollTop = logDiv.scrollHeight;
}

ws.onopen = (event) => {
    add_log_entry('Connection opened.');
}

ws.onmessage = function(event) {
    let rec = JSON.parse(event.data);
    console.debug("Message received:", rec);

    if (rec.method === "write") {
        add_log_entry(rec.data);
    }
}
