import React, { useEffect, useState } from "react";
import { View, Text, TouchableOpacity, StyleSheet, ActivityIndicator } from "react-native";

export default function HomeScreen() {
  const [message, setMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const fetchMessage = async () => {
    setLoading(true);
    try {
      // ⚠️ For physical devices, replace localhost with your computer's IP (e.g. 192.168.x.x)
      const response = await fetch("http://127.0.0.1:8001/");
      const text = await response.text();
      setMessage(text);
    } catch (error) {
      setMessage("⚠️ Could not connect to backend");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMessage();
  }, []);

  return (
    <View style={styles.container}>

      {loading ? (
        <ActivityIndicator size="large" color="#a47148" />
      ) : (
        <Text style={styles.message}>{message}</Text>
      )}

      <TouchableOpacity style={styles.button} onPress={fetchMessage}>
        <Text style={styles.buttonText}>Refresh</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#fffaf3",
    alignItems: "center",
    justifyContent: "center",
    padding: 20,
  },
  title: {
    fontSize: 28,
    fontWeight: "bold",
    color: "#6b4f4f",
    marginBottom: 30,
  },
  message: {
    fontSize: 18,
    color: "#444",
    marginBottom: 20,
    textAlign: "center",
  },
  button: {
    backgroundColor: "#a47148",
    paddingVertical: 12,
    paddingHorizontal: 28,
    borderRadius: 10,
  },
  buttonText: {
    color: "white",
    fontSize: 18,
    fontWeight: "500",
  },
});
