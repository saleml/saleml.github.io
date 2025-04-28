import React, { useState, useEffect } from "react";
import axios from "axios";
import "./style.css"; // Import your new CSS

function HyperstackVMManager() {
  const [vms, setVMs] = useState([]);

  // Generic function to proxy API calls
  const callApi = async (method, path, data = null) => {
    try {
      const response = await axios({
        method: method,
        url: '/api/hyperstack', // Use the relative path to the Netlify function
        // Send original path and method in the request body or headers
        data: {
          targetPath: path,
          targetMethod: method,
          payload: data // Include payload for methods like POST if needed later
        },
        headers: {
          // No API key sent from the browser
          accept: "application/json",
        },
      });
      return response.data;
    } catch (error) {
      console.error(`API call failed for ${method} ${path}:`, error);
      // Extract backend error message if available
      const errorMessage = error.response?.data?.error || error.message || `API call failed for ${method} ${path}.`;
      alert(errorMessage);
      throw error; // Re-throw the error to stop further processing if needed
    }
  };

  const fetchVMs = async () => {
    try {
      // Pass original path and method
      const data = await callApi('get', '/core/virtual-machines');
      setVMs(data.instances || []);
    } catch (error) {
       // Error is already logged and alerted in callApi
      console.error("Failed to process VMs after fetch:", error);
    }
  };

  const handleHibernate = async (vmId) => {
     try {
      // Pass original path and method
      await callApi('get', `/core/virtual-machines/${vmId}/hibernate`);
      alert(`VM ${vmId} hibernated successfully.`);
      fetchVMs(); // Refresh the list
     } catch (error) {
      // Error is already logged and alerted in callApi
      console.error(`Processing error after hibernate attempt for VM ${vmId}:`, error);
     }
  };

  const handleRelaunch = async (vmId) => {
    try {
      // Pass original path and method
      await callApi('get', `/core/virtual-machines/${vmId}/hibernate-restore`);
      alert(`VM ${vmId} restored successfully.`);
      fetchVMs(); // Refresh the list
    } catch (error) {
      // Error is already logged and alerted in callApi
      console.error(`Processing error after relaunch attempt for VM ${vmId}:`, error);
    }
  };

  useEffect(() => {
    fetchVMs();
  }, []);

  return (
    <div>
      <h1>Salem's group Hyperstack VM Manager</h1>
      <table>
        <thead>
          <tr>
            <th>VM ID</th>
            <th>Name</th>
            <th>Status</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {vms.map((vm) => (
            <tr key={vm.id}>
              <td>{vm.id}</td>
              <td>{vm.name}</td>
              <td>{vm.status}</td>
              <td>
                {vm.status === "ACTIVE" ? (
                  <button onClick={() => handleHibernate(vm.id)}>Hibernate</button>
                ) : (
                  <button
                    className="relaunch"
                    onClick={() => handleRelaunch(vm.id)}
                  >
                    Relaunch
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <footer>Powered by Hyperstack API</footer>
    </div>
  );
}

export default HyperstackVMManager;