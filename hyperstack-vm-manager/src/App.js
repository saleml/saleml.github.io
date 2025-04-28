import React, { useState, useEffect, useCallback } from "react";
import axios from "axios";
import "./style.css"; // Import your new CSS

function HyperstackVMManager() {
  const [vms, setVMs] = useState([]);

  // Wrap callApi in useCallback. It has no external dependencies from component scope.
  const callApi = useCallback(async (method, path, data = null) => {
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
  }, []); // Empty dependency array as it doesn't rely on component state/props

  // Wrap fetchVMs in useCallback. It depends on callApi.
  const fetchVMs = useCallback(async () => {
    try {
      // Pass original path and method
      const data = await callApi('get', '/core/virtual-machines');
      setVMs(data.instances || []);
    } catch (error) {
       // Error is already logged and alerted in callApi
      console.error("Failed to process VMs after fetch:", error);
    }
  }, [callApi]); // Dependency array includes callApi

  // Wrap handleHibernate in useCallback. It depends on callApi and fetchVMs.
  const handleHibernate = useCallback(async (vmId) => {
     try {
      // Pass original path and method
      await callApi('get', `/core/virtual-machines/${vmId}/hibernate`);
      alert(`VM ${vmId} hibernated successfully.`);
      fetchVMs(); // Refresh the list
     } catch (error) {
      // Error is already logged and alerted in callApi
      console.error(`Processing error after hibernate attempt for VM ${vmId}:`, error);
     }
  }, [callApi, fetchVMs]); // Dependency array includes callApi and fetchVMs

  // Wrap handleRelaunch in useCallback. It depends on callApi and fetchVMs.
  const handleRelaunch = useCallback(async (vmId) => {
    try {
      // Pass original path and method
      await callApi('get', `/core/virtual-machines/${vmId}/hibernate-restore`);
      alert(`VM ${vmId} restored successfully.`);
      fetchVMs(); // Refresh the list
    } catch (error) {
      // Error is already logged and alerted in callApi
      console.error(`Processing error after relaunch attempt for VM ${vmId}:`, error);
    }
  }, [callApi, fetchVMs]); // Dependency array includes callApi and fetchVMs

  useEffect(() => {
    fetchVMs();
  }, [fetchVMs]); // Keep fetchVMs here, it's now stable thanks to useCallback

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