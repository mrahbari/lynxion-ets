## **Task: Extend Watcher → Engine → Fusion → Strategy → Broker Pipeline With Broker Tracking**

### **Background**

In our system, **Watchers** are responsible for detecting symbols and sending that data to the next components in the pipeline:

**Watcher → Engine → Fusion → Strategy → Broker**

Watchers can already read data from different brokers. Now we need to **complete and extend this functionality**.

### **Goal**

When a Watcher reads data from a specific broker, it must **include the broker’s name in its output** so that all downstream components can use this information.

### **Requirements**

1. **Add broker identifier to Watcher output.**
   Whenever a Watcher reads from a broker, it must attach the broker name to the result it sends forward.

2. **Ensure the entire pipeline carries this broker information.**
   The broker identifier must pass through:
   **Watcher → Engine → Fusion → Strategy → Broker**

3. **Enable future configuration rules.**
   After this change, the system should support configurations such as:

   * “If a Spike Watcher detects a symbol, submit the order *only* to BingX.”
   * “Or: allow sending the order to any available broker.”

4. **Maintain stability.**
   All modifications must be implemented carefully to avoid breaking the existing flow.

