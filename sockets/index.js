const {WebSocket, WebSocketServer} = require('ws');
const wss = new WebSocketServer({port:8081});
const ip = require('ip');
console.dir(ip.address()+':8081');

wss.on('connection', (ws) => {
	ws.on('error', console.error);
	ws.on('message', (data, isBinary) => {
		wss.clients.forEach(client => {
			if (client !== ws && client.readyState === WebSocket.OPEN) {
				client.send(data, {binary: isBinary})
			}
		});
	});
});
