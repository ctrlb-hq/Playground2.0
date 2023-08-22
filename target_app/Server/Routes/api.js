const express = require('express');
const router = express.Router();

"use strict";

router.post('/winner',
  gameWinner
);

router.post('/move',
  nextMove
);

function gameWinner(req,res) {
	let input = JSON.parse(req.body.board);
	let output = winner(input);
  	res.json({winner : output});
}

function nextMove(req,res) {
	let input = JSON.parse(req.body.board);
	let output = move(input);
	res.json({nextMove : output});
}

/*
move function accepts tic-tac-toe array as a parameter and returns index position for the next move.
*/
function move(board){
	switch (gameCounter(board)) {
		case 0:
		case 1:
			return firstMove(board);
			break;
		case 2:
			return secondMove(board);
			break;
		case 3:
		case 4:
		case 5:
		case 6:
		case 7:
		case 8:
			return incrementalMove(board);
			break;
	}

}


/*
winner function accepts tic-tac-toe board array as a paramenter and determines if the game has a winner.
Returns 'Tie', 'In Progress', 'X wins', 'O wins' 
*/

function winner(board){

	if (!winningCombo(board) && board.indexOf('') > -1) return 'In Progress';
	if (!winningCombo(board) && board.indexOf('') === -1) return 'Tie';
	if (winningCombo(board)) return board[winningCombo(board)[0]] + ' Wins';

}

/*
winningCombo function accepts an array as a parameter and returns 'undefined' if there is no winning tic-tac-toe combination.
If there is a winning tic-tac-toe combination, the function will return an array containing the winning combination
*/

function winningCombo(board){
	if (board === undefined) return undefined
	var winningCombinations = [
		[0, 1, 2],
		[3, 4, 5],
		[6, 7, 8],
		[0, 3, 6],
		[1, 4, 7],
		[2, 5, 8],
		[0, 4, 8],
		[2, 4, 6]
	];

	var winner = winningCombinations.find(combo =>
    board[combo[0]] !== '' &&
    board[combo[0]] === board[combo[1]] &&
    board[combo[1]] === board[combo[2]]
  );

  return winner

}

// /*
// gameCounter function counts the number of moves in a tic-tac-toe array
// */
function gameCounter(board){
	let counter = 0

	board.forEach(element =>{
		if(element !== '') counter++
	});

	return counter;
}

/*
firstMove function returns the position (assuming the tic-tac-toe board is numbered 0-8) a player should take for their first move.
If an empty board is passed in, the function assumes it is making the first move in the game.
*/

function firstMove(board){

	return board.indexOf('X') === 4 || board.indexOf('X') === -1 ? 0 : 4

}

/*
secondMove function returns the optimal move for player X given player O position choice.
*/

function secondMove(board){

	switch (board.indexOf('O')) {
		case 1:
		case 2:
			return 3;
			break;
		case 3:
		case 4:
		case 6:
			return 1;
			break;
		case 5:
			return 4;
			break;
		case 7:
		case 8:
			return 2;
			break;
	}

}





/*
winningMove function accepts an array as a parameter and returns 'false' if there is no winning spot on the board.
If there is a winning tic-tac-toe position, the function will return the index position on the board.
*/

function winningMove(board){
	var winningCombinations = [
		[0, 1, 2],
		[3, 4, 5],
		[6, 7, 8],
		[0, 3, 6],
		[1, 4, 7],
		[2, 5, 8],
		[0, 4, 8],
		[2, 4, 6]
	];

	var winningIndex = false;

	var move = winningCombinations.find(combo => {
		let xCount = 0;
		let yCount = 0;
		let emptyCount = 0;
		let emptyIndex;

		combo.reduce((n, val, index) => {
			if(board[val] === 'X') xCount++
			if(board[val] === 'O') yCount++
			if(board[val] === '') {
				emptyCount++
				emptyIndex = val;
			}
		}, 0)

		if ((xCount || yCount) === 2 && emptyCount === 1) winningIndex = emptyIndex

		return (xCount || yCount) === 2 && emptyCount === 1;
	
	});

	return winningIndex;

}


// /*
// gameCounter function counts the number of moves in a tic-tac-toe array
// */
function gameCounter(board){
	let counter = 0

	board.forEach(element =>{
		if(element !== '') counter++
	});

	return counter;
}

/*
incrementalMove function returns the optimal move given opponents position choice.
*/

function incrementalMove(board){

	if (typeof winningMove(board) === 'number') {
		return winningMove(board);
	}

	switch (gameCounter(board)) {
		case 3:
			if(board[0] === 'X' && board[5] === 'X') return 7;
			if(board[0] === 'X' && board[7] === 'X') return 5;
			if(board[0] === 'X' && board[8] === 'X') return 1;
			if(board[1] === 'X' && board[3] === 'X') return 2;
			if(board[1] === 'X' && board[5] === 'X') return 0;
			if(board[1] === 'X' && board[6] === 'X') return 5;
			if(board[1] === 'X' && board[7] === 'X') return 0;
			if(board[1] === 'X' && board[8] === 'X') return 3;
			if(board[2] === 'X' && board[3] === 'X') return 7;
			if(board[2] === 'X' && board[6] === 'X') return 1;
			if(board[2] === 'X' && board[7] === 'X') return 3;
			if(board[3] === 'X' && board[5] === 'X') return 0;
			if(board[3] === 'X' && board[7] === 'X') return 0;
			if(board[3] === 'X' && board[8] === 'X') return 1;
			if(board[4] === 'X' && board[8] === 'X') return 2;
			if(board[5] === 'X' && board[6] === 'X') return 1;
			if(board[5] === 'X' && board[7] === 'X') return 2;
			break;
		case 4:
			if(board[1] === 'O' && board[6] === 'O') return 4;
			if(board[2] === 'O' && board[3] === 'O') return 4;
			if(board[1] === 'O' && board[8] === 'O') return 6;
			break;
		default:
			return board.indexOf('');
	}

}








module.exports = router;