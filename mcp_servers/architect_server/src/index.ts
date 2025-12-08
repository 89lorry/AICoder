#!/usr/bin/env node
/**
 * Architect MCP Server
 * Exposes software architecture design capabilities via MCP protocol
 */

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ErrorCode,
  ListToolsRequestSchema,
  McpError,
} from '@modelcontextprotocol/sdk/types.js';
import axios from 'axios';

// Configuration from environment
const GEMINI_API_KEY = process.env.GEMINI_API_KEY;
const GEMINI_ENDPOINT = process.env.GEMINI_ENDPOINT || 
  'https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent';

if (!GEMINI_API_KEY) {
  throw new Error('GEMINI_API_KEY environment variable is required');
}

interface ArchitectureResult {
  analysis: {
    components: string[];
    dependencies: string[];
    architecture_type: string;
    complexity: string;
    summary: string;
  };
  file_structure: {
    files: Record<string, string>;
    entry_point: string;
    class_definitions?: Record<string, string>;
  };
  detailed_plan: {
    overview: string;
    file_plans: Record<string, any>;
    implementation_order: string[];
    test_considerations: string[];
    notes: string[];
  };
  requirements: string;
  timestamp: string;
}

class ArchitectMCPServer {
  private server: Server;
  private axiosInstance;

  constructor() {
    this.server = new Server(
      {
        name: 'architect-mcp-server',
        version: '1.0.0',
      },
      {
        capabilities: {
          tools: {},
        },
      }
    );

    this.axiosInstance = axios.create({
      timeout: 90000, // 90 second timeout
    });

    this.setupToolHandlers();
    
    // Error handling
    this.server.onerror = (error) => console.error('[MCP Error]', error);
    process.on('SIGINT', async () => {
      await this.server.close();
      process.exit(0);
    });
  }

  private setupToolHandlers() {
    // List available tools
    this.server.setRequestHandler(ListToolsRequestSchema, async () => ({
      tools: [
        {
          name: 'create_architecture',
          description: 'Analyze requirements and create comprehensive software architecture',
          inputSchema: {
            type: 'object',
            properties: {
              requirements: {
                type: 'string',
                description: 'Natural language description of software requirements',
              },
            },
            required: ['requirements'],
          },
        },
      ],
    }));

    // Handle tool calls
    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      if (request.params.name !== 'create_architecture') {
        throw new McpError(
          ErrorCode.MethodNotFound,
          `Unknown tool: ${request.params.name}`
        );
      }

      const args = request.params.arguments as { requirements?: string };
      if (!args.requirements || typeof args.requirements !== 'string') {
        throw new McpError(
          ErrorCode.InvalidParams,
          'Missing or invalid requirements parameter'
        );
      }

      try {
        const result = await this.createArchitecture(args.requirements);
        
        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify(result, null, 2),
            },
          ],
        };
      } catch (error) {
        console.error('Error creating architecture:', error);
        return {
          content: [
            {
              type: 'text',
              text: `Error creating architecture: ${error instanceof Error ? error.message : String(error)}`,
            },
          ],
          isError: true,
        };
      }
    });
  }

  private async createArchitecture(requirements: string): Promise<ArchitectureResult> {
    console.error('[Architect] Creating architecture for requirements...');
    
    const prompt = `
╔══════════════════════════════════════════════════════════════════════════╗
║          🚨 CRITICAL ARCHITECTURE RULES - READ FIRST 🚨                 ║
╚══════════════════════════════════════════════════════════════════════════╝

Create a COMPLETE architectural plan for the following requirements in a SINGLE response:

Requirements:
${requirements}

Provide a comprehensive JSON response with ALL of the following sections:

1. "analysis": {
    "components": [EXACTLY 3 main components/modules - NO MORE],
    "dependencies": [external libraries needed],
    "architecture_type": "CLI/API/GUI/etc",
    "complexity": "simple/medium/complex",
    "summary": "brief project summary"
}

2. "file_structure": {
    "files": {
        "main.py": "Contains ALL core classes and application logic",
        "utils.py": "ONLY helper functions (imports from main.py)",
        "test_data.py": "ONLY sample data (imports from main.py)",
        "README.md": "Project documentation"
    },
    "entry_point": "main.py",
    "class_definitions": {
        "ClassName": "main.py"  // ALL classes defined in main.py
    }
}

3. "detailed_plan": {
    "overview": "overall architecture description",
    "file_plans": {
        "main.py": {
            "purpose": "what it does",
            "classes": ["Class1", "Class2"],
            "functions": ["func1", "func2"],
            "key_logic": "main logic flow",
            "design_principles": [
                "Data retrieval methods RETURN values",
                "Query/search methods RETURN results",
                "main() handles printing"
            ]
        },
        "utils.py": {
            "purpose": "what it does",
            "functions": ["helper1", "helper2"],
            "imports": ["from main import ClassName"]
        }
    },
    "implementation_order": ["main.py", "utils.py", "test_data.py"],
    "test_considerations": ["what to test"],
    "notes": ["important notes"]
}

CRITICAL RULES:
- EXACTLY 3 components in analysis
- ALL classes defined in main.py ONLY
- utils.py and test_data.py import from main.py
- NO duplicate class definitions
- Return ONLY valid JSON, no markdown

Response MUST be parseable JSON starting with { and ending with }.
`;

    try {
      const response = await this.axiosInstance.post(
        `${GEMINI_ENDPOINT}?key=${GEMINI_API_KEY}`,
        {
          contents: [
            {
              parts: [{ text: prompt }]
            }
          ],
          generationConfig: {
            temperature: 0.2,
          }
        },
        {
          headers: {
            'Content-Type': 'application/json',
          }
        }
      );

      const responseText = response.data.candidates[0].content.parts[0].text;
      console.error('[Architect] Received response from LLM');
      
      // Parse the JSON response
      const architecture = this.parseArchitectureResponse(responseText);
      architecture.requirements = requirements;
      architecture.timestamp = new Date().toISOString();
      
      console.error('[Architect] Architecture created successfully');
      return architecture;
      
    } catch (error) {
      if (axios.isAxiosError(error)) {
        throw new Error(`LLM API error: ${error.response?.data?.error?.message || error.message}`);
      }
      throw error;
    }
  }

  private parseArchitectureResponse(responseText: string): ArchitectureResult {
    try {
      // Remove markdown code blocks if present
      let cleanedText = responseText;
      const lines = responseText.split('\n');
      const filteredLines = lines.filter(line => {
        const stripped = line.trim();
        return stripped !== '```json' && stripped !== '```' && stripped !== '```JSON';
      });
      cleanedText = filteredLines.join('\n');
      
      // Extract JSON
      const startIdx = cleanedText.indexOf('{');
      const endIdx = cleanedText.lastIndexOf('}') + 1;
      
      if (startIdx === -1 || endIdx === 0) {
        throw new Error('No JSON found in response');
      }
      
      const jsonStr = cleanedText.substring(startIdx, endIdx);
      const parsed = JSON.parse(jsonStr);
      
      // Validate structure
      if (!parsed.analysis || !parsed.file_structure || !parsed.detailed_plan) {
        throw new Error('Missing required sections in architecture response');
      }
      
      return parsed as ArchitectureResult;
      
    } catch (error) {
      console.error('[Architect] Error parsing response:', error);
      // Return fallback structure
      return {
        analysis: {
          components: ['Core Application', 'Data Management', 'User Interface'],
          dependencies: [],
          architecture_type: 'CLI',
          complexity: 'medium',
          summary: 'Multi-component application',
        },
        file_structure: {
          files: {
            'main.py': 'Main entry point and core classes',
            'utils.py': 'Utility functions',
            'test_data.py': 'Sample data',
            'README.md': 'Documentation',
          },
          entry_point: 'main.py',
        },
        detailed_plan: {
          overview: 'Simple application architecture',
          file_plans: {
            'main.py': {
              purpose: 'Core application logic',
              classes: [],
              functions: [],
              key_logic: 'Main application flow',
            },
          },
          implementation_order: ['main.py', 'utils.py', 'test_data.py'],
          test_considerations: ['Basic functionality tests'],
          notes: ['Fallback architecture used due to parsing error'],
        },
        requirements: '',
        timestamp: new Date().toISOString(),
      };
    }
  }

  async run() {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    console.error('Architect MCP server running on stdio');
  }
}

const server = new ArchitectMCPServer();
server.run().catch(console.error);
