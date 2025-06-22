import Header from "../components/Header";
import { useState, useEffect } from "react";
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

const apiKey = import.meta.env.VITE_REACT_APP_STREAM_API_KEY;
const userId = "js-user";

const ChatPage = () => {
  const [client, setClient] = useState(null);
  const [loading, setLoading] = useState(true);
  const [channel, setChannel] = useState(null);
  const [messages, setMessages] = useState([
    { role: 'system', content: 'You are a helpful assistant.' }
  ]);
  const [error, setError] = useState("");

  useEffect(() => {
    const setupStreamUI = async () => {
      try {
        console.log("Setting up Stream Chat with API key:", apiKey ? "Available" : "Missing");

        // 1. Get token from backend
        const tokenResponse = await fetch('http://127.0.0.1:8000/token', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ userId }),
        });

        if (!tokenResponse.ok) throw new Error('Failed to get token from server');
        const { token } = await tokenResponse.json();

        if (!token) throw new Error('No token received from server');
        console.log("Received token from server");

        // 2. Initialize Stream chat client with the token
        const chatClient = StreamChat.getInstance(apiKey);
        await chatClient.connectUser(
          { id: userId, name: 'User' },
          token
        );
        console.log("Connected user to Stream Chat");

        // 3. Create or get existing channel
        const localChannel = chatClient.channel("messaging", "ai-assistant", {
          name: "AI Assistant Chat",
          created_by: { id: userId }
        });

        console.log("Watching channel");
        await localChannel.watch();

        setChannel(localChannel);
        setClient(chatClient);
      } catch (err) {
        console.error("Error setting up chat UI:", err);
        setError(err.message || "Failed to initialize chat");
      } finally {
        setLoading(false);
      }
    };

    setupStreamUI();

    return () => {
      if (client) client.disconnectUser();
    };
  }, []);

  const handleSendMessage = async (messageData) => {
    // Extract text from messageData - Stream Chat sends different object structure
    const messageText = typeof messageData === 'string'
      ? messageData
      : messageData?.text || messageData?.message?.text;

    if (!messageText || !messageText.trim()) return;

    try {
      // Add user message to the UI
      await channel.sendMessage({
        text: messageText,
        user: { id: userId }
      });

      // Update messages array for OpenAI
      const updatedMessages = [...messages, { role: 'user', content: messageText }];
      setMessages(updatedMessages);

      // Send to OpenAI through backend
      const response = await fetch('http://127.0.0.1:8000/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ messages: updatedMessages }),
      });

      if (!response.ok) throw new Error('Failed to get response');

      const data = await response.json();

      // Add AI response to the UI
      await channel.sendMessage({
        text: data.message,
        user: { id: 'ai-assistant', name: 'AI Assistant' }
      });

      // Update messages array with AI response
      setMessages([...updatedMessages, { role: 'assistant', content: data.message }]);
    } catch (error) {
      console.error("Error:", error);
      if (channel) {
        await channel.sendMessage({
          text: "Sorry, there was an error processing your request.",
          user: { id: 'ai-assistant', name: 'AI Assistant' }
        });
      }
    }
  };

  if (loading) return <div>Loading chat interface...</div>;
  if (error) return <div>Error: {error}</div>;
  if (!apiKey) return <div>Error: Stream Chat API key is missing</div>;
  if (!client) return <div>Error: Could not initialize Stream Chat client</div>;
  if (!channel) return <div>Error: Could not create chat channel</div>;

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
                  // Ensure message exists before processing
                  if (message && (message.text || (message.message && message.message.text))) {
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