function zoomIn(element) {
    element.style.transform = "scale(1.2)";
    element.style.transition = "transform 0.3s ease";
}

function zoomOut(element) {
    element.style.transform = "scale(1)";
    element.style.transition = "transform 0.3s ease";
}


document.getElementById("searchInput").addEventListener("keypress", function (event) {
    if (event.key === 'Enter') {
        filterCrops();
    }
});

function filterCrops() {
    var input, filter, crops, crop, i, txtValue, matchedCrops;
    input = document.getElementById("searchInput");
    filter = input.value.toUpperCase();
    crops = document.getElementsByClassName("elem");
    matchedCrops = [];

    for (i = 0; i < crops.length; i++) {
        crop = crops[i];
        txtValue = crop.innerText || crop.textContent;
        if (txtValue.toUpperCase().indexOf(filter) > -1) {
            matchedCrops.push(crop);
        }
    }

   
    for (i = 0; i < crops.length; i++) {
        crops[i].style.display = "none";
    }

   
    for (i = 0; i < matchedCrops.length; i++) {
        matchedCrops[i].style.display = "";
        
        var parent = matchedCrops[i].parentNode;
        parent.insertBefore(matchedCrops[i], parent.firstChild);
    }
}


var fixed = document.querySelector(".fixed");
var elements = document.querySelectorAll(".elem");

elements.forEach(function (element) {
    element.addEventListener("mouseenter", function () {
        fixed.style.display = "block";
    });

    element.addEventListener("mouseleave", function () {
        fixed.style.display = "none";
    });
});


elements.forEach(function (element) {
    element.addEventListener("mouseenter", function () {
        var image = element.getAttribute("data-image");
        fixed.style.backgroundImage = `url(${image})`;
    });

    element.addEventListener("mouseleave", function () {
        fixed.style.backgroundImage = 'none';
    });
});

// mobile view




document.addEventListener("DOMContentLoaded", function () {
    var mobileMenuBtn = document.querySelector(".mobile-menu-btn");
    var mainNav = document.querySelector(".main-nav");

    mobileMenuBtn.addEventListener("click", function () {
        mainNav.classList.toggle("show");
    });
});



var tl = gsap.timeline();

tl.from(".loader h1", {
    x: -500,
    duration: 1,
    onStart: time
});

function time() {
    var time = 0;
    var intervalID = setInterval(function() {
        time += Math.floor(Math.random() * 10);
        console.log(time);
        if (time < 100) {
            document.querySelector(".loader h1").innerHTML = ` Loading ${time} %`;
        } else {
            time = 100;
            document.querySelector(".loader h1").innerHTML = `Loading ${time} %`;
            clearInterval(intervalID);
            tl.to(".loader", {
                y: "-100%",
                delay:0.3
            });
        }
    }, 100);
}
