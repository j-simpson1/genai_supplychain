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
  const getAuthToken = useCallback(async () => {
    const response = await fetch(`${BACKEND_URL}/token`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ userId: USER_ID }),
    });

    if (!response.ok) {
      throw new Error('Failed to get authentication token from server');
    }

    const { token } = await response.json();
    if (!token) {
      throw new Error('No token received from server');
    }

    return token;
  }, []);

  // Initialize Stream Chat client
  const initializeStreamClient = useCallback(async (token) => {
    const chatClient = StreamChat.getInstance(API_KEY);

    await chatClient.connectUser(
      { id: USER_ID, name: 'User' },
      token
    );

    console.log("Connected user to Stream Chat");
    return chatClient;
  }, []);

  // Create or get existing chat channel
  const setupChannel = useCallback(async (chatClient) => {
    const chatChannel = chatClient.channel(CHANNEL_TYPE, CHANNEL_ID, {
      name: "AI Assistant Chat",
      created_by: { id: USER_ID }
    });

    console.log("Setting up channel");
    await chatChannel.watch();

    return chatChannel;
  }, []);

  // Send message to AI backend and get response
  const sendToAI = useCallback(async (messageHistory) => {
    const response = await fetch(`${BACKEND_URL}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ messages: messageHistory }),
    });

    if (!response.ok) {
      throw new Error('Failed to get AI response');
    }

    const data = await response.json();
    return data.message;
  }, []);

  // Send error message to chat
  const sendErrorMessage = useCallback(async (channel, errorMessage = "Sorry, there was an error processing your request.") => {
    if (channel) {
      await channel.sendMessage({
        text: errorMessage,
        user: { id: 'ai-assistant', name: 'AI Assistant' }
      });
    }
  }, []);

  // Main message handler
  const handleSendMessage = useCallback(async (messageData) => {
    const messageText = extractMessageText(messageData);

    if (!messageText?.trim()) return;

    try {
      // Send user message to Stream Chat UI
      await channel.sendMessage({
        text: messageText,
        user: { id: USER_ID }
      });

      // Update message history for AI context
      const updatedMessages = [...messages, { role: 'user', content: messageText }];
      setMessages(updatedMessages);

      // Get AI response
      const aiResponse = await sendToAI(updatedMessages);

      // Send AI response to Stream Chat UI
      await channel.sendMessage({
        text: aiResponse,
        user: { id: 'ai-assistant', name: 'AI Assistant' }
      });

      // Update message history with AI response
      const finalMessages = [...updatedMessages, { role: 'assistant', content: aiResponse }];
      setMessages(finalMessages);

    } catch (error) {
      console.error("Error handling message:", error);
      await sendErrorMessage(channel);
    }
  }, [channel, messages, extractMessageText, sendToAI, sendErrorMessage]);

  // Setup chat interface on component mount
  useEffect(() => {
    const setupStreamChat = async () => {
      try {
        console.log("Setting up Stream Chat with API key:", API_KEY ? "Available" : "Missing");

        if (!API_KEY) {
          throw new Error('Stream Chat API key is missing');
        }

        // Get authentication token
        const token = await getAuthToken();
        console.log("Received token from server");

        // Initialize Stream Chat client
        const chatClient = await initializeStreamClient(token);

        // Setup chat channel
        const chatChannel = await setupChannel(chatClient);

        // Update state
        setClient(chatClient);
        setChannel(chatChannel);

      } catch (err) {
        console.error("Error setting up chat interface:", err);
        setError(err.message || "Failed to initialize chat");
      } finally {
        setLoading(false);
      }
    };

    setupStreamChat();

    // Cleanup on component unmount
    return () => {
      if (client) {
        client.disconnectUser();
      }
    };
  }, [getAuthToken, initializeStreamClient, setupChannel, client]);

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