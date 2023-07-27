var express = require('express');
var path = require('path');
const fs = require('fs');
var bodyParser = require('body-parser');
var cookieParser = require('cookie-parser');
var api = require('./Routes/api');
const cors = require('cors'); // Import the cors middleware

var app = express();
app.use(cors()); // Enable CORS for all routes

app.set('port', (process.argv[2] || 8000));

var server = app.listen(app.get('port'), function() {
  console.log('listening on port ',app.get('port'));
});

app.use(bodyParser.urlencoded({ extended: true }));
app.use(express.static(path.join(__dirname,'../../templates')));

app.use(cookieParser());

app.use(bodyParser.json());

app.use('/api', (req, res, next) => {
  res.header('Access-Control-Allow-Origin', '*');
  res.header('Access-Control-Allow-Method', 'GET, POST, HEAD, OPTIONS, PUT');
  res.header('Access-Control-Allow-Headers', 'Origin, Content-Type, Authorization');
  next();
});

app.use('/api', api);

// Add a route to serve the contents of api.js
app.get('/api/js', (req, res) => {
  const apiJSFilePath = path.join(__dirname, '../Server/Routes/api.js');
  fs.readFile(apiJSFilePath, 'utf8', (err, data) => {
    if (err) {
      console.error('Error reading api.js:', err);
      return res.status(500).send('Internal Server Error');
    }
    res.setHeader('Content-Type', 'application/javascript');
    res.send(data);
  });
});

app.get('/', function (req, res) {
	//res.status(200).send('Hi. Tic Tac Toe Homepage');
  res.sendFile(path.join(__dirname,'../../templates','tic-tac-toe.html'));
});

app.all('*', function (req, res) {
  res.status(404).send('Nothing Here');
});

module.exports = server;