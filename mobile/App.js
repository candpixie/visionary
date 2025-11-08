import React, { useState, useEffect, useRef } from 'react';
import { StyleSheet, Text, View, TouchableOpacity, Alert, Platform, Image } from 'react-native';
import { CameraView, useCameraPermissions } from 'expo-camera';
import { StatusBar } from 'expo-status-bar';
import HomeScreen from './components/HomeScreen';
import SignInScreen from './components/SignInScreen';
import CreateAccountScreen from './components/CreateAccountScreen';
import AssessmentScreen from './components/AssessmentScreen';

// WebSocket connection for streaming
let ws = null;
let frameInterval = null;
let isCapturing = false; // Flag to prevent concurrent captures

export default function App() {
  const [currentScreen, setCurrentScreen] = useState('home'); // 'home', 'signin', 'createaccount', 'assessment', or 'camera'
  const [permission, requestPermission] = useCameraPermissions();
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [serverUrl, setServerUrl] = useState('ws://10.28.39.17:8765'); // Change to your laptop's IP
  const cameraRef = useRef(null);
  const [isStreaming, setIsStreaming] = useState(false);

  const connectWebSocket = () => {
    // Close existing connection if any
    if (ws) {
      try {
        ws.close();
      } catch (e) {
        console.log('Error closing existing connection:', e);
      }
    }

    setIsConnecting(true);
    console.log('Attempting to connect to:', serverUrl);

    try {
      // React Native has built-in WebSocket support
      ws = new WebSocket(serverUrl);

      ws.onopen = () => {
        console.log('✅ Connected to server');
        setIsConnected(true);
        setIsConnecting(false);
        Alert.alert('Connected', 'Successfully connected to GlaucoGuard server');
      };

      ws.onerror = (error) => {
        console.error('❌ WebSocket error:', error);
        setIsConnected(false);
        setIsConnecting(false);
        Alert.alert(
          'Connection Error', 
          `Failed to connect to server at ${serverUrl}\n\nMake sure:\n1. Server is running on your laptop\n2. IP address is correct\n3. Both devices are on same Wi-Fi network`
        );
      };

      ws.onclose = (event) => {
        console.log('Disconnected from server. Code:', event.code, 'Reason:', event.reason);
        setIsConnected(false);
        setIsConnecting(false);
        if (event.code !== 1000) { // Not a normal closure
          console.log('Unexpected disconnection');
        }
      };

      ws.onmessage = (event) => {
        // Handle server messages if needed
        console.log('Message from server:', event.data);
      };

      // Set a timeout to show error if connection takes too long
      setTimeout(() => {
        if (ws && ws.readyState === WebSocket.CONNECTING) {
          console.log('Connection timeout');
          ws.close();
          setIsConnecting(false);
          Alert.alert(
            'Connection Timeout',
            `Could not connect to ${serverUrl}\n\nPlease check:\n1. Server is running\n2. IP address is correct\n3. Firewall allows port 8765`
          );
        }
      }, 10000); // 10 second timeout

    } catch (error) {
      console.error('Error creating WebSocket:', error);
      setIsConnecting(false);
      Alert.alert('Error', `Failed to create connection: ${error.message}\n\nCheck your server URL: ${serverUrl}`);
    }
  };

  const startStreaming = () => {
    if (!isConnected || !cameraRef.current) {
      Alert.alert('Error', 'Camera or connection not ready');
      return;
    }

    setIsStreaming(true);
    isCapturing = false;
    
    // Send start message to server to explicitly resume streaming
    if (ws && ws.readyState === 1) {
      try {
        ws.send(JSON.stringify({
          type: 'start_streaming',
          timestamp: Date.now(),
        }));
        console.log('Start streaming message sent to server');
      } catch (error) {
        console.error('Error sending start message:', error);
      }
    }
    
    // Capture frames and send to server
    frameInterval = setInterval(async () => {
      // Skip if already capturing or if camera/connection not ready
      if (isCapturing || !cameraRef.current || !ws || ws.readyState !== 1) {
        return;
      }

      isCapturing = true;
      try {
        const photo = await cameraRef.current.takePictureAsync({
          quality: 0.05, // Ultra low quality for maximum speed and minimal lag
          base64: true,
          skipProcessing: true,
          exif: false, // Disable EXIF data to reduce size
          allowsEditing: false,
        });

        if (photo && photo.base64 && ws && ws.readyState === 1) {
          // Send frame to server
          const message = JSON.stringify({
            type: 'video_frame',
            data: photo.base64,
            timestamp: Date.now(),
          });
          ws.send(message);
        }
      } catch (error) {
        // Only log if it's not the unmounted error (which is expected if stopping)
        if (error.message && !error.message.includes('unmounted')) {
          console.error('Error capturing frame:', error);
        }
      } finally {
        isCapturing = false;
      }
    }, 16); // Send ~60 frames per second for ultra-fast real-time video
  };

  const stopStreaming = () => {
    setIsStreaming(false);
    isCapturing = false; // Reset capture flag
    // Immediately stop capturing frames
    if (frameInterval) {
      clearInterval(frameInterval);
      frameInterval = null;
    }
    // Send stop message to server BEFORE clearing interval to ensure it's sent
    if (ws && ws.readyState === 1) {
      try {
        ws.send(JSON.stringify({
          type: 'stop_streaming',
          timestamp: Date.now(),
        }));
        console.log('Stop streaming message sent to server');
      } catch (error) {
        console.error('Error sending stop message:', error);
      }
    }
  };

  const disconnect = () => {
    stopStreaming();
    if (ws) {
      try {
        // Send disconnect message before closing
        if (ws.readyState === 1) {
          ws.send(JSON.stringify({
            type: 'phone_disconnecting',
            timestamp: Date.now(),
          }));
          // Give it a moment to send
          setTimeout(() => {
            if (ws) {
              ws.close();
              ws = null;
            }
          }, 100);
        } else {
          ws.close();
          ws = null;
        }
      } catch (error) {
        console.error('Error sending disconnect message:', error);
        if (ws) {
          ws.close();
          ws = null;
        }
      }
    }
    setIsConnected(false);
  };

  const handleNavigateToCamera = () => {
    setCurrentScreen('camera');
  };

  const handleNavigateToSignIn = () => {
    setCurrentScreen('signin');
  };

  const handleNavigateToCreateAccount = () => {
    setCurrentScreen('createaccount');
  };

  const handleNavigateToHome = () => {
    // Stop streaming and disconnect when going back to home
    if (isStreaming) {
      stopStreaming();
    }
    if (isConnected) {
      disconnect();
    }
    setCurrentScreen('home');
  };

  const handleSignIn = () => {
    // TODO: Implement actual sign in logic
    // Navigate to assessment screen
    console.log('Sign in successful');
    setCurrentScreen('assessment');
  };

  const handleCreateAccount = () => {
    // TODO: Implement actual account creation logic
    // Navigate to assessment screen
    console.log('Account created successfully');
    setCurrentScreen('assessment');
  };

  const handleAssessmentComplete = (answers) => {
    // TODO: Save assessment answers
    console.log('Assessment completed with answers:', answers);
    // Navigate to camera screen after assessment
    setCurrentScreen('camera');
  };

  // Show home screen
  if (currentScreen === 'home') {
    return <HomeScreen onNavigateToCamera={handleNavigateToCamera} onNavigateToSignIn={handleNavigateToSignIn} onNavigateToCreateAccount={handleNavigateToCreateAccount} />;
  }

  // Show sign in screen
  if (currentScreen === 'signin') {
    return <SignInScreen onSignIn={handleSignIn} onBack={handleNavigateToHome} onNavigateToCreateAccount={handleNavigateToCreateAccount} />;
  }

  // Show create account screen
  if (currentScreen === 'createaccount') {
    return <CreateAccountScreen onCreateAccount={handleCreateAccount} onBack={handleNavigateToHome} onNavigateToSignIn={handleNavigateToSignIn} />;
  }

  // Show assessment screen
  if (currentScreen === 'assessment') {
    return <AssessmentScreen onComplete={handleAssessmentComplete} onBack={handleNavigateToHome} />;
  }

  // Camera permission checks
  if (!permission) {
    return (
      <View style={styles.container}>
        <Text>Requesting camera permission...</Text>
      </View>
    );
  }

  if (!permission.granted) {
    return (
      <View style={styles.container}>
        <Text style={styles.errorText}>No access to camera</Text>
        <Text style={styles.helpText}>Please enable camera permissions</Text>
        <TouchableOpacity style={styles.button} onPress={requestPermission}>
          <Text style={styles.buttonText}>Grant Permission</Text>
        </TouchableOpacity>
        <TouchableOpacity style={[styles.button, styles.disconnectButton]} onPress={handleNavigateToHome}>
          <Text style={styles.buttonText}>Back to Home</Text>
        </TouchableOpacity>
      </View>
    );
  }

  // Camera screen
  return (
    <View style={styles.container}>
      <StatusBar style="light" />
      
      <View style={styles.header}>
        <View style={styles.headerLeft}>
          <Image 
            source={require('./assets/logo.png')} 
            style={styles.logo}
            resizeMode="contain"
          />
          <Text style={styles.title}>GLAUCOGUARD</Text>
        </View>
        <View style={[styles.statusIndicator, isConnected && styles.statusConnected]}>
          <Text style={styles.statusText}>
            {isConnected ? 'CONNECTED' : 'DISCONNECTED'}
          </Text>
        </View>
      </View>

      <CameraView
        ref={cameraRef}
        style={styles.camera}
        facing="back"
      />

      <View style={styles.controls}>
        {!isConnected && !isConnecting ? (
          <TouchableOpacity style={styles.button} onPress={connectWebSocket}>
            <Text style={styles.buttonText}>CONNECT TO SERVER</Text>
          </TouchableOpacity>
        ) : isConnecting ? (
          <TouchableOpacity style={[styles.button, styles.connectingButton]} disabled>
            <Text style={styles.buttonText}>CONNECTING...</Text>
          </TouchableOpacity>
        ) : (
          <>
            {!isStreaming ? (
              <TouchableOpacity style={[styles.button, styles.startButton]} onPress={startStreaming}>
                <Text style={styles.buttonText}>START STREAMING</Text>
              </TouchableOpacity>
            ) : (
              <TouchableOpacity style={[styles.button, styles.stopButton]} onPress={stopStreaming}>
                <Text style={styles.buttonText}>STOP STREAMING</Text>
              </TouchableOpacity>
            )}
            <TouchableOpacity style={[styles.button, styles.disconnectButton]} onPress={disconnect}>
              <Text style={styles.buttonText}>DISCONNECT</Text>
            </TouchableOpacity>
          </>
        )}
        <TouchableOpacity style={[styles.button, { backgroundColor: '#444' }]} onPress={handleNavigateToHome}>
          <Text style={styles.buttonText}>← BACK TO HOME</Text>
        </TouchableOpacity>
      </View>

      <View style={styles.info}>
        <Text style={styles.infoText}>
          Server: {serverUrl}
        </Text>
        <Text style={styles.infoText}>
          Status: {isConnecting ? 'Connecting...' : isConnected ? (isStreaming ? 'Streaming...' : 'Connected') : 'Disconnected'}
        </Text>
        {ws && (
          <Text style={styles.infoText}>
            WS State: {ws.readyState === 0 ? 'CONNECTING' : ws.readyState === 1 ? 'OPEN' : ws.readyState === 2 ? 'CLOSING' : 'CLOSED'}
          </Text>
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#1a1a1a',
  },
  header: {
    padding: 20,
    paddingTop: 50,
    backgroundColor: '#000',
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  headerLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
  },
  logo: {
    width: 40,
    height: 40,
    marginRight: 10,
  },
  title: {
    color: '#00CED1',
    fontSize: 18,
    fontWeight: 'bold',
    fontFamily: 'monospace',
    textShadowColor: '#008B8B',
    textShadowOffset: { width: 0, height: 0 },
    textShadowRadius: 8,
  },
  statusIndicator: {
    backgroundColor: '#660000',
    paddingHorizontal: 15,
    paddingVertical: 5,
    borderRadius: 5,
  },
  statusConnected: {
    backgroundColor: '#00CED1',
  },
  statusText: {
    color: '#000',
    fontWeight: 'bold',
    fontSize: 12,
    fontFamily: 'monospace',
  },
  camera: {
    flex: 1,
  },
  controls: {
    padding: 20,
    backgroundColor: '#000',
  },
  button: {
    backgroundColor: '#333',
    padding: 15,
    borderRadius: 5,
    marginBottom: 10,
    alignItems: 'center',
  },
  startButton: {
    backgroundColor: '#00CED1',
    borderWidth: 1,
    borderColor: '#48D1CC',
    shadowColor: '#008B8B',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.4,
    shadowRadius: 8,
  },
  stopButton: {
    backgroundColor: '#ff0000',
  },
  disconnectButton: {
    backgroundColor: '#666',
  },
  connectingButton: {
    backgroundColor: '#ffaa00',
    opacity: 0.7,
  },
  buttonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: 'bold',
    fontFamily: 'monospace',
  },
  info: {
    padding: 15,
    backgroundColor: '#0a0a0a',
  },
  infoText: {
    color: '#00CED1',
    fontSize: 12,
    fontFamily: 'monospace',
    marginBottom: 5,
  },
  errorText: {
    color: '#ff0000',
    fontSize: 18,
    textAlign: 'center',
    marginBottom: 10,
    fontFamily: 'monospace',
  },
  helpText: {
    color: '#00CED1',
    fontSize: 14,
    textAlign: 'center',
    fontFamily: 'monospace',
  },
});

