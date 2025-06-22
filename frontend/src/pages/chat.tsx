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

// Initial system message for AI context
const INITIAL_SYSTEM_MESSAGE = {
  role: 'system',
  content: 'You are a helpful assistant.'
};

// Sidebar component for chat history
const ChatHistorySidebar = ({
  conversations,
  activeConversationId,
  onSelectConversation,
  onNewConversation,
  onDeleteConversation
}) => {
  return (
    <div className="chat-history-sidebar">
      <div className="sidebar-header">
        <h3>Chat History</h3>
        <button
          className="new-chat-btn"
          onClick={onNewConversation}
          title="New Chat"
        >
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
            <path d="M10 4v12m6-6H4" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
          </svg>
        </button>
      </div>
      <div className="conversation-list">
        {conversations.length === 0 ? (
          <div className="empty-state">No conversations yet</div>
        ) : (
          conversations.map((conv) => (
            <div
              key={conv.id}
              className={`conversation-item ${conv.id === activeConversationId ? 'active' : ''}`}
              onClick={() => onSelectConversation(conv.id)}
            >
              <div className="conversation-info">
                <div className="conversation-title">
                  {conv.title || `Chat ${conv.id.slice(-4)}`}
                </div>
                <div className="conversation-date">
                  {new Date(conv.createdAt).toLocaleDateString()}
                </div>
              </div>
              <button
                className="delete-btn"
                onClick={(e) => {
                  e.stopPropagation();
                  onDeleteConversation(conv.id);
                }}
                title="Delete conversation"
              >
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                  <path d="M2 4h12M5 4V2h6v2m-7 0v10h8V4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              </button>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

const ChatPage = () => {
  // State management
  const [client, setClient] = useState(null);
  const [channel, setChannel] = useState(null);
  const [conversations, setConversations] = useState([]);
  const [activeConversationId, setActiveConversationId] = useState(null);
  const [messages, setMessages] = useState([INITIAL_SYSTEM_MESSAGE]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [sidebarOpen, setSidebarOpen] = useState(true);

  // Utility function to extract message text from different Stream Chat formats
  const extractMessageText = useCallback((messageData) => {
    if (typeof messageData === 'string') return messageData;
    return messageData?.text || messageData?.message?.text || '';
  }, []);

  // Load conversations from localStorage
  const loadConversations = useCallback(() => {
    const saved = localStorage.getItem('chatConversations');
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        setConversations(parsed);
        return parsed;
      } catch (e) {
        console.error('Error loading conversations:', e);
      }
    }
    return [];
  }, []);

  // Save conversations to localStorage
  const saveConversations = useCallback((convs) => {
    localStorage.setItem('chatConversations', JSON.stringify(convs));
  }, []);

  // Create a new conversation
  const createNewConversation = useCallback(() => {
    const newConv = {
      id: `conv-${Date.now()}`,
      title: '',
      messages: [INITIAL_SYSTEM_MESSAGE],
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString()
    };

    const updatedConvs = [newConv, ...conversations];
    setConversations(updatedConvs);
    saveConversations(updatedConvs);
    setActiveConversationId(newConv.id);
    setMessages([INITIAL_SYSTEM_MESSAGE]);

    // Create new channel
    if (client) {
      setupChannel(client, newConv.id);
    }

    return newConv;
  }, [conversations, client, saveConversations]);

  // Select a conversation
  const selectConversation = useCallback((convId) => {
    const conv = conversations.find(c => c.id === convId);
    if (conv) {
      setActiveConversationId(convId);
      setMessages(conv.messages || [INITIAL_SYSTEM_MESSAGE]);

      // Switch to the conversation's channel
      if (client) {
        setupChannel(client, convId);
      }
    }
  }, [conversations, client]);

  // Delete a conversation
  const deleteConversation = useCallback((convId) => {
    const updatedConvs = conversations.filter(c => c.id !== convId);
    setConversations(updatedConvs);
    saveConversations(updatedConvs);

    // If deleting active conversation, switch to a new one
    if (convId === activeConversationId) {
      if (updatedConvs.length > 0) {
        selectConversation(updatedConvs[0].id);
      } else {
        createNewConversation();
      }
    }
  }, [conversations, activeConversationId, saveConversations, selectConversation, createNewConversation]);

  // Update conversation with new messages
  const updateConversation = useCallback((convId, newMessages) => {
    const updatedConvs = conversations.map(conv => {
      if (conv.id === convId) {
        // Generate title from first user message if not set
        let title = conv.title;
        if (!title && newMessages.length > 1) {
          const firstUserMsg = newMessages.find(m => m.role === 'user');
          if (firstUserMsg) {
            title = firstUserMsg.content.slice(0, 50) + (firstUserMsg.content.length > 50 ? '...' : '');
          }
        }

        return {
          ...conv,
          messages: newMessages,
          title,
          updatedAt: new Date().toISOString()
        };
      }
      return conv;
    });

    setConversations(updatedConvs);
    saveConversations(updatedConvs);
  }, [conversations, saveConversations]);

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
  const setupChannel = useCallback(async (chatClient, channelId) => {
    try {
      console.log(`Setting up channel ${channelId}...`);

      // Add client-level event listener for debugging
      chatClient.on('message.new', event => {
        console.log('New message received by client:', event);
      });

      const chatChannel = chatClient.channel(CHANNEL_TYPE, channelId, {
        name: `AI Assistant Chat ${channelId}`,
        created_by: { id: USER_ID },
        members: [USER_ID, 'ai-assistant'],
      });

      // Add channel-level event listener
      chatChannel.on('message.new', event => {
        console.log('New message received in channel:', event);
      });

      // Create or watch the channel with the full message history option
      const state = await chatChannel.watch({
        state: true,
        watchers: { limit: 10 },
        presence: true
      });

      // Mark channel as read after watching
      try {
        await chatChannel.markRead();
      } catch (markReadError) {
        console.warn("Could not mark channel as read:", markReadError);
      }

      setChannel(chatChannel);
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

      // Ensure messages have the correct format with role and content
      const formattedMessages = messageHistory.map(msg => ({
        role: msg.role,
        content: msg.content
      }));

      const response = await fetch(`${BACKEND_URL}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: formattedMessages,
          channel_id: activeConversationId || `conv-${Date.now()}`
        }),
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`AI request failed: ${response.status} ${response.statusText} - ${errorText}`);
      }

      const data = await response.json();
      console.log("✓ AI response received");
      return data.message;
    } catch (error) {
      console.error("Error getting AI response:", error);
      throw error;
    }
  }, [activeConversationId]);

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

      // Update conversation in storage
      updateConversation(activeConversationId, finalMessages);

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
  }, [channel, client, messages, activeConversationId, extractMessageText, sendToAI, updateConversation]);

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

        // Load existing conversations or create first one
        const loadedConvs = loadConversations();
        let activeConv;

        if (loadedConvs.length === 0) {
          // Create first conversation
          const newConv = {
            id: `conv-${Date.now()}`,
            title: '',
            messages: [INITIAL_SYSTEM_MESSAGE],
            createdAt: new Date().toISOString(),
            updatedAt: new Date().toISOString()
          };
          setConversations([newConv]);
          saveConversations([newConv]);
          activeConv = newConv;
        } else {
          activeConv = loadedConvs[0];
          setMessages(activeConv.messages || [INITIAL_SYSTEM_MESSAGE]);
        }

        setActiveConversationId(activeConv.id);

        // Setup chat channel for active conversation
        const chatChannel = await setupChannel(userClient, activeConv.id);
        if (!mounted) return;

        // Update state
        setClient(userClient);

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
      <div className="chat-page-wrapper">
        <ChatHistorySidebar
          conversations={conversations}
          activeConversationId={activeConversationId}
          onSelectConversation={selectConversation}
          onNewConversation={createNewConversation}
          onDeleteConversation={deleteConversation}
        />
        <div className={`chat-container ${sidebarOpen ? 'with-sidebar' : ''}`}>
          <button
            className="sidebar-toggle"
            onClick={() => setSidebarOpen(!sidebarOpen)}
            title={sidebarOpen ? 'Hide sidebar' : 'Show sidebar'}
          >
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
              {sidebarOpen ? (
                <path d="M11 6l-4 4 4 4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              ) : (
                <path d="M9 6l4 4-4 4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              )}
            </svg>
          </button>
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
      </div>
    </>
  );
};

export default ChatPage;