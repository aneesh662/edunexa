document.addEventListener("DOMContentLoaded",()=>{
  document.querySelectorAll("form").forEach(f=>f.addEventListener("submit",()=>{const b=f.querySelector("button[type=submit],button:not(.btn-close)");if(b && !f.dataset.confirmDelete){b.dataset.old=b.innerHTML; b.innerHTML='<span class="spinner-border spinner-border-sm me-1"></span> Please wait';}}));
});
