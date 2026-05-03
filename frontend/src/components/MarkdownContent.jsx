import ReactMarkdown from "react-markdown";
import SyntaxHighlighter from "react-syntax-highlighter/dist/esm/prism-light";
import bash from "react-syntax-highlighter/dist/esm/languages/prism/bash";
import docker from "react-syntax-highlighter/dist/esm/languages/prism/docker";
import javascript from "react-syntax-highlighter/dist/esm/languages/prism/javascript";
import json from "react-syntax-highlighter/dist/esm/languages/prism/json";
import jsx from "react-syntax-highlighter/dist/esm/languages/prism/jsx";
import python from "react-syntax-highlighter/dist/esm/languages/prism/python";
import yaml from "react-syntax-highlighter/dist/esm/languages/prism/yaml";
import oneDark from "react-syntax-highlighter/dist/esm/styles/prism/one-dark";
import oneLight from "react-syntax-highlighter/dist/esm/styles/prism/one-light";

SyntaxHighlighter.registerLanguage("bash", bash);
SyntaxHighlighter.registerLanguage("docker", docker);
SyntaxHighlighter.registerLanguage("dockerfile", docker);
SyntaxHighlighter.registerLanguage("javascript", javascript);
SyntaxHighlighter.registerLanguage("js", javascript);
SyntaxHighlighter.registerLanguage("json", json);
SyntaxHighlighter.registerLanguage("jsx", jsx);
SyntaxHighlighter.registerLanguage("python", python);
SyntaxHighlighter.registerLanguage("py", python);
SyntaxHighlighter.registerLanguage("yaml", yaml);
SyntaxHighlighter.registerLanguage("yml", yaml);

export default function MarkdownContent({ children, theme = "dark" }) {
  return (
    <ReactMarkdown
      components={{
        a({ children: linkChildren, ...props }) {
          return (
            <a {...props} target="_blank" rel="noreferrer">
              {linkChildren}
            </a>
          );
        },
        code({ children: codeChildren, className, ...props }) {
          const match = /language-(\w+)/.exec(className || "");
          const code = String(codeChildren).replace(/\n$/, "");

          if (!match) {
            return (
              <code className="markdown-inline-code" {...props}>
                {codeChildren}
              </code>
            );
          }

          return (
            <SyntaxHighlighter
              PreTag="div"
              language={match[1]}
              style={theme === "light" ? oneLight : oneDark}
              customStyle={{
                margin: 0,
                borderRadius: "10px",
                background: "var(--input-bg)",
                fontSize: "0.86rem",
              }}
              codeTagProps={{
                style: {
                  fontFamily:
                    'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace',
                },
              }}
            >
              {code}
            </SyntaxHighlighter>
          );
        },
      }}
    >
      {children}
    </ReactMarkdown>
  );
}
