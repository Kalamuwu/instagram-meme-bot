// webserver/websocket.js
// sets up and manages the websocket.

const protocol = (location.protocol==="http:") ? 'ws' : 'wss';
const url = `${protocol}://${location.host}/ws/app/`;
const ws = new ReconnectingWebSocket(url, null, {debug: true, reconnectInterval: 3000});

ws.onopen = (event) => {
    document.getElementById("log").insertAdjacentHTML('beforeend', '<div class="logentry"> <span> Connection opened. </span> </div>');
}

ws.onmessage = function(event) {
    let rec = JSON.parse(event.data)
    console.debug("Message received:", rec)

    if (rec.method === "write") {
        let string = `<div class="logentry"> <span> ${rec.data} </span> </div>`;
        document.getElementById("log").insertAdjacentHTML('beforeend', string);
    }
}
