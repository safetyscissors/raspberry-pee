const {WebSocket, WebSocketServer} = require('ws');
const {exec} = require('child_process');
const wss = new WebSocketServer({port:8081});
const ip = require('ip');
console.dir(ip.address()+':8081');

const startMsg = Buffer.from('gameStart');

wss.on('connection', (ws) => {
	ws.on('error', console.error);
	ws.on('message', (data, isBinary) => {
		if (startMsg.equals(data)) {
			console.log('starting');
			exec('sh /home/math27182/Documents/windy/gray/start.sh', (err, stdout, stderr) => {
				console.log(stdout);
			});
			console.log('resume');
			return;
		}
		wss.clients.forEach(client => {
			if (client !== ws && client.readyState === WebSocket.OPEN) {
				client.send(data, {binary: isBinary})
			}
		});
	});
});
