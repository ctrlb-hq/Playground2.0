import React from 'react';
import { CodeEditor, CodeOutput } from 'react-run-code';

class MyCodeScreen extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      code: '',
      output: '',
    };
  }

  handleCodeChange = (newCode) => {
    this.setState({ code: newCode });
  };

  handleRunCode = () => {
    // Execute the code and update the output state
    // You can use any method to execute the code, such as eval() or a code execution library
    // For security reasons, make sure to validate and sanitize the code before executing it
    // Here's an example using eval():
    try {
      const output = eval(this.state.code);
      this.setState({ output: output.toString() });
    } catch (error) {
      this.setState({ output: error.toString() });
    }
  };

  render() {
    return (
      <div>
        <CodeEditor
          code={this.state.code}
          onChange={this.handleCodeChange}
          onRun={this.handleRunCode}
        />
        <CodeOutput output={this.state.output} />
      </div>
    );
  }
}

export default MyCodeScreen;