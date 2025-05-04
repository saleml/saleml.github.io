---
layout: about
permalink: /teaching/
published: true
---

## Teaching

<style>
.teaching-item {
  margin-bottom: 1.5em;
}

.teaching-toggle {
  cursor: pointer;
  display: block;
  border-bottom: 1px solid #d3d3d3;
  padding-bottom: 5px;
  user-select: none;
  font-weight: 500;
  margin-bottom: 0.5em;
}

.teaching-toggle:hover {
    color: #007bff; /* Or your preferred hover color */
}


.teaching-icon {
  color: #d3d3d3;
  font-size: 0.8em;
  float: right;
  line-height: inherit; /* Align icon vertically */
}

.teaching-content {
  display: none;
  padding-left: 1em; /* Indent the content */
  margin-top: 0.5em;
}

.teaching-content ul {
  list-style-type: disc;
  margin-left: 1.5em; /* Indent list items */
  padding-left: 0;
}

.teaching-content li {
  margin-bottom: 0.3em;
}

</style>

<div class="teaching-list">

  <div class="teaching-item">
    <h3 class="teaching-toggle">
      Deep Learning course - SKEMA 2025
      <span class="teaching-icon">+</span>
    </h3>
    <div class="teaching-content">
      <ul>
        <li>Mastère Spécialisé® Chef de Projet Intelligence Artificielle</li>
        <li><a href="{{site.baseurl}}/sk25/">Course Materials</a></li>
      </ul>
    </div>
  </div>

  <div class="teaching-item">
    <h3 class="teaching-toggle">
      ML702: Advanced Machine Learning (MSc course) @ MBZUAI 2025
      <span class="teaching-icon">+</span>
    </h3>
    <div class="teaching-content">
      <ul>
        <li>Co-taught with Eric Moulines and Zhiqiang Shen</li>
        <li>Topics: Active Learning, Bayesian Optimization, Reinforcement learning</li>
        <li><a href="https://saleml-teaching-interactive-mp-mdp-interactive-chclfk.streamlit.app/" target="_blank">Interactive Simulations of Markov Processes and Markov Decision Processes</a></li>
      </ul>
    </div>
  </div>

  <div class="teaching-item">
    <h3 class="teaching-toggle">
      ML805: Advanced Machine Learning (PhD course) @ MBZUAI 2025
      <span class="teaching-icon">+</span>
    </h3>
    <div class="teaching-content">
      <ul>
        <li>Co-taught with Michalis Vazirgiannis, Tongliang Liu, and Yuanzhi Li</li>
        <li>Topics: Diffusion models, GFlowNets</li>
      </ul>
    </div>
  </div>

  <div class="teaching-item">
    <h3 class="teaching-toggle">
      Mathematical Foundations of Machine Learning (Pre-doctoral course) @ UM6P 2025
      <span class="teaching-icon">+</span>
    </h3>
    <div class="teaching-content">
      <ul>
        <li>Co-taught with Hachem Madmoun</li>
        <li>Topics: Linear algebra, probability theory, probabilistic machine learning, neural networks</li>
      </ul>
    </div>
  </div>

  <div class="teaching-item">
    <h3 class="teaching-toggle">
      ML801: Foundations and Advanced Topics in Machine Learning (PhD course) @ MBZUAI 2025
      <span class="teaching-icon">+</span>
    </h3>
    <div class="teaching-content">
      <ul>
        <li>Co-taught with Martin Takac</li>
        <li>Topics: Reinforcement Learning</li>
      </ul>
    </div>
  </div>

  <div class="teaching-item">
    <h3 class="teaching-toggle">
      MTH703: Mathematics for Theoretical Computer Science (MSc course) @ MBZUAI 2024
      <span class="teaching-icon">+</span>
    </h3>
    <div class="teaching-content">
      <ul>
        <li>Co-taught with Tongliang Liu and Jin Tian</li>
        <li>Topics: Spectral graph theory, error correcting codes, linear programming...</li>
      </ul>
    </div>
  </div>

  <div class="teaching-item">
    <h3 class="teaching-toggle">
      Mathematical Foundations of Machine Learning (Pre-doctoral course) @ UM6P 2024
      <span class="teaching-icon">+</span>
    </h3>
    <div class="teaching-content">
      <ul>
        <li>Co-taught with Hachem Madmoun</li>
        <li>Topics: Linear algebra, probability theory, probabilistic machine learning, neural networks</li>
      </ul>
    </div>
  </div>

</div>

<script>
  document.addEventListener('DOMContentLoaded', () => {
    const toggles = document.querySelectorAll('.teaching-toggle');

    toggles.forEach(toggle => {
      toggle.addEventListener('click', () => {
        const content = toggle.nextElementSibling;
        const icon = toggle.querySelector('.teaching-icon');

        if (content.style.display === 'none' || content.style.display === '') {
          content.style.display = 'block';
          icon.textContent = '-';
        } else {
          content.style.display = 'none';
          icon.textContent = '+';
        }
      });
    });
  });
</script> 