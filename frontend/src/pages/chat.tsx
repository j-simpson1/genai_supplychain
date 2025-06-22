import Header from "../components/Header";
import { useState, useEffect, useCallback } from "react";
import {
  Chat,
  Channel,
  Window,
  ChannelHeader,
  MessageList,
  MessageInput,
} from "stream-chat-react";
import { StreamChat } from "stream-chat";
import "stream-chat-react/dist/css/v2/index.css";
import "./chat.scss";

// Constants
const API_KEY = import.meta.env.VITE_REACT_APP_STREAM_API_KEY;
const USER_ID = "js-user";
const BACKEND_URL = "http://127.0.0.1:8000";
const CHANNEL_TYPE = "messaging";
const CHANNEL_ID = "ai-assistant";

// Initial system message for AI context
const INITIAL_SYSTEM_MESSAGE = {
  role: 'system',
  content: 'You are a helpful assistant.'
};

const ChatPage = () => {
  // State management
  const [client, setClient] = useState(null);
  const [channel, setChannel] = useState(null);
  const [messages, setMessages] = useState([INITIAL_SYSTEM_MESSAGE]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Utility function to extract message text from different Stream Chat formats
  const extractMessageText = useCallback((messageData) => {
    if (typeof messageData === 'string') return messageData;
    return messageData?.text || messageData?.message?.text || '';
  }, []);

  // Get authentication token from backend
  const getAuthToken = useCallback(async (userId) => {
    try {
      console.log(`Requesting token for user: ${userId}`);
      const response = await fetch(`${BACKEND_URL}/token`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ userId }),
      });

      if (!response.ok) {
        throw new Error(`Failed to get authentication token: ${response.status} ${response.statusText}`);
      }

      const { token } = await response.json();
      if (!token) {
        throw new Error('No token received from server');
      }

      console.log(`Token received for ${userId}`);
      return token;
    } catch (error) {
      console.error(`Error getting token for ${userId}:`, error);
      throw error;
    }
  }, []);

  // Initialize Stream Chat client
  const initializeStreamClient = useCallback(async (token, userId, userName) => {
    try {
      console.log(`Initializing client for ${userName}...`);
      const chatClient = new StreamChat(API_KEY);

      await chatClient.connectUser(
        { id: userId, name: userName },
        token
      );

      console.log(`✓ Connected ${userName} to Stream Chat`);
      return chatClient;
    } catch (error) {
      console.error(`Error connecting ${userName}:`, error);
      throw error;
    }
  }, []);

  // Create or get existing chat channel
  const setupChannel = useCallback(async (chatClient) => {
    try {
      console.log("Setting up channel...");

      const chatChannel = chatClient.channel(CHANNEL_TYPE, CHANNEL_ID, {
        name: "AI Assistant Chat",
        created_by: { id: USER_ID }
      });

      await chatChannel.watch();
      console.log("✓ Channel setup complete");

      return chatChannel;
    } catch (error) {
      console.error("Error setting up channel:", error);
      throw error;
    }
  }, []);

  // Send message to AI backend and get response
  const sendToAI = useCallback(async (messageHistory) => {
    try {
      console.log("Sending message to AI backend...");
      const response = await fetch(`${BACKEND_URL}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messages: messageHistory }),
      });

      if (!response.ok) {
        throw new Error(`AI request failed: ${response.status} ${response.statusText}`);
      }

      const data = await response.json();
      console.log("✓ AI response received");
      return data.message;
    } catch (error) {
      console.error("Error getting AI response:", error);
      throw error;
    }
  }, []);

  // Main message handler
  const handleSendMessage = useCallback(async (messageData) => {
    const messageText = extractMessageText(messageData);

    if (!messageText?.trim()) return;

    // Check if client and channel are still valid
    if (!channel || !client) {
      console.error("Chat components not available");
      return;
    }

    try {
      console.log(`User message: "${messageText}"`);

      // Send user message to Stream Chat UI first
      await channel.sendMessage({
        text: messageText,
      });

      // Update message history for AI context
      const updatedMessages = [...messages, { role: 'user', content: messageText }];
      setMessages(updatedMessages);

      // Get AI response (the server will send the AI message to the chat)
      const aiResponse = await sendToAI(updatedMessages);
      console.log(`AI response received: "${aiResponse}"`);

      // Update local message history with AI response
      const finalMessages = [...updatedMessages, { role: 'assistant', content: aiResponse }];
      setMessages(finalMessages);

    } catch (error) {
      console.error("Error in message handler:", error);

      // Send error message through the channel
      if (channel && client && client.user) {
        try {
          await channel.sendMessage({
            text: `Error: ${error.message}`,
          });
        } catch (sendError) {
          console.error("Could not send error message:", sendError);
        }
      }
    }
  }, [channel, client, messages, extractMessageText, sendToAI]);

  // Setup chat interface on component mount
  useEffect(() => {
    let userClient = null;
    let mounted = true;

    const setupStreamChat = async () => {
      try {
        console.log("=== Setting up Stream Chat ===");
        console.log("API key available:", API_KEY ? "✓" : "✗");

        if (!API_KEY) {
          throw new Error('Stream Chat API key is missing');
        }

        // Get authentication token for user
        const userToken = await getAuthToken(USER_ID);
        if (!mounted) return;

        // Initialize Stream Chat client
        userClient = await initializeStreamClient(userToken, USER_ID, 'User');
        if (!mounted) return;

        // Setup chat channel
        const chatChannel = await setupChannel(userClient);
        if (!mounted) return;

        // Update state
        setClient(userClient);
        setChannel(chatChannel);

        console.log("=== Stream Chat setup complete ===");

      } catch (err) {
        console.error("=== Stream Chat setup failed ===", err);
        setError(err.message || "Failed to initialize chat");
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    };

    setupStreamChat();

    // Cleanup on component unmount
    return () => {
      mounted = false;
      const cleanup = async () => {
        try {
          console.log("Cleaning up chat client...");

          // Clear state first to prevent any further operations
          setChannel(null);
          setClient(null);

          // Disconnect client
          if (userClient) {
            await userClient.disconnectUser();
          }

          console.log("✓ Cleanup complete");
        } catch (error) {
          console.error("Error during cleanup:", error);
        }
      };
      cleanup();
    };
  }, []);

  // Render loading state
  if (loading) {
    return <div className="chat-loading">Loading chat interface...</div>;
  }

  // Render error states
  if (error) {
    return <div className="chat-error">Error: {error}</div>;
  }

  if (!API_KEY) {
    return <div className="chat-error">Error: Stream Chat API key is missing</div>;
  }

  if (!client || !channel) {
    return <div className="chat-error">Error: Could not initialize chat interface</div>;
  }

  // Main render
  return (
    <>
      <Header />
      <div className="chat-container">
        <Chat client={client}>
          <Channel channel={channel}>
            <Window>
              <ChannelHeader title="AI Assistant" />
              <MessageList />
              <MessageInput
                overrideSubmitHandler={(message) => {
                  const messageText = extractMessageText(message);
                  if (messageText?.trim()) {
                    handleSendMessage(message);
                    return true;
                  }
                  return false;
                }}
              />
            </Window>
          </Channel>
        </Chat>
      </div>
    </>
  );
};

export default ChatPage;