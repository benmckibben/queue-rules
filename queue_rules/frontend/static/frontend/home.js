function getCSRF() {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, 10) === ('csrftoken=')) {
                cookieValue = decodeURIComponent(cookie.substring(10));
                break;
            }
        }
    }
    return cookieValue;
}

function appendToSequenceList(spotifyId, name) {
    var itemNumber = document.getElementsByClassName('seq-list-item').length + 1;
    if (name === undefined) {
        name = spotifyId;
    }

    $("#modalSequenceList").append(
        `<button type="button" class="list-group-item list-group-item-action seq-list-item" id="seqListItem${itemNumber}" onclick="removeSeqListItem(${itemNumber})">${name}</button>`
    );
    $(`#seqListItem${itemNumber}`).data("spotifyId", spotifyId);
}
    
function sequenceListAddButtonOnClick() {
    var newVal = $("#seqAddText").val();
    if (newVal !== "") {
        appendToSequenceList(newVal);
        $("#seqAddText").val("");
    }
}

function removeSeqListItem(number) {
    $("#seqListItem" + number).remove();
}

function populateRuleModalBody(ruleId) {
    $("#saveRuleButton").html(`Save`);

    $("#ruleModalBody").html(`
        <form>
            <div class="form-group">
                <label for="trigger-song">After this song plays:</label>
                <input type="text" class="form-control" id="trigger-song" aria-describedby="triggerHelp">
                <small id="triggerHelp" class="form-text">
                    Paste a Spotify URI here, such as spotify:track:6sGiI7V9kgLNEhPIxEJDii.
                    <br>You can get this by right-clicking on a song, then clicking Share -> Copy Spotify URI.
                </small>
                <br><br>
                <label for="song-sequence">Then play these songs:</label>
                <div id="song-sequence" class="input-group mb-3" aria-describedby="sequenceHelp">
                    <input type="text" id="seqAddText" class="form-control" aria-label="Song to queue">
                    <div class="input-group-append">
                        <button class="btn btn-outline-secondary" type="button" onclick="sequenceListAddButtonOnClick()">
                            <svg width="1em" height="1em" viewBox="0 0 16 16" class="bi bi-plus" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
                                <path fill-rule="evenodd" d="M8 3.5a.5.5 0 0 1 .5.5v4a.5.5 0 0 1-.5.5H4a.5.5 0 0 1 0-1h3.5V4a.5.5 0 0 1 .5-.5z"/>
                                <path fill-rule="evenodd" d="M7.5 8a.5.5 0 0 1 .5-.5h4a.5.5 0 0 1 0 1H8.5V12a.5.5 0 0 1-1 0V8z"/>
                            </svg>
                        </button>
                    </div>
                </div>
                <small id="sequenceHelp" class="form-text">
                    Again, paste Spotify URIs here. Click the tracks once added to remove them.
                </small>
                <br>
                <div class="list-group" id="modalSequenceList"></div>
            </div>
        </form>
    `);

    var seqAddText = document.getElementById("seqAddText");
    seqAddText.addEventListener("keyup", function(event) {
        if (event.key === "Enter") {
            sequenceListAddButtonOnClick();
        }
    });

    if (ruleId !== null) {
        $.getJSON(`/api/rules/${ruleId}/`)
            .done(function(data) {
                $("#ruleModalLabel").html("Edit Rule");
                $("#trigger-song").data("ruleId", ruleId);
                $("#trigger-song").val(`spotify:track:${data["trigger_song_spotify_id"]}`);
                $.each(data["song_sequence"], function(i, x) {
                    appendToSequenceList(x["song_spotify_id"], x["name"]);
                });

                var checkValue = data["is_active"] ? "checked" : "";
                $("#ruleModalBody").prepend(`
                    <div class="form-check">
                        <input class="form-check-input" type="checkbox" id="ruleActive" ${checkValue}>
                        <label class="form-check-label" for="ruleActive">
                            Active
                        </label>
                    </div><br>
                `);

                $("#ruleModalBody").prepend(`
                    <button id="deleteRuleButton" type="button" class="btn btn-danger" data-dismiss="modal" onclick="deleteRule()">Delete rule</button><br>
                `);
            }).fail(function() {
                $("#ruleModalLabel").html("Error");
                $("#ruleModalBody").html("There was an error loading the rule. Please close this dialog and try again.");
                $("#saveRuleButton").remove();
            });
    } else {
        $("#ruleModalLabel").html("New Rule");
    }
}

function getRuleFormData() {
    var data = {};
    
    data["trigger_song_spotify_id"] = $("#trigger-song").val().replace('spotify:track:', '');
    
    data["song_sequence"] = [];
    $.each($(".seq-list-item"), function(i, x) {
        data["song_sequence"].push({
            "song_spotify_id": $(x).data("spotifyId").replace('spotify:track:', ''),
            "sequence_number": i,
        });
    });

    var ruleId = $("#trigger-song").data()["ruleId"];
    if (ruleId !== undefined) {
        data["id"] = ruleId;
        data["is_active"] = $('#ruleActive').is(":checked");
    }

    return data;
}

function deleteRule() {
    var ruleId = $("#trigger-song").data()["ruleId"];

    $.ajaxSetup({
        headers: {"X-CSRFToken": getCSRF()}
    });

    $.ajax({
        type: "DELETE",
        url: `/api/rules/${ruleId}/`,
        success: function() {
            $("#ruleModal").modal("hide");
            populateRuleList();
        },
    });
}

function submitForm() {
    $("#saveRuleButton").html(`
        <div class="spinner-border spinner-border-sm" role="status">
            <span class="sr-only">Saving...</span>
        </div>
    `);

    var data = getRuleFormData();
    var method = data["id"] === undefined ? "POST" : "PUT";
    var url = data["id"] === undefined ? "/api/rules/create/" : `/api/rules/${data["id"]}/`;

    $.ajaxSetup({
        headers: {"X-CSRFToken": getCSRF()}
    });

    $.ajax({
        type: method,
        url: url,
        data: JSON.stringify(data),
        contentType: "application/json",
        success: function() {
            $("#ruleModal").modal("hide");
            populateRuleList();
        },
        error: function(xhr, status) {
            $("#saveRuleButton").html("Save");
            var errorMessage = "Uh oh, an unknown error occurred.";
            if (xhr.status === 400) {
                errorMessage = JSON.parse(xhr.responseText)[0];
            }

            $("#ruleModalBody").append(`
                <div class="alert alert-danger alert-dismissible fade show" role="alert">
                    ${errorMessage}
                    <button type="button" class="close" data-dismiss="alert" aria-label="Close">
                        <span aria-hidden="true">&times;</span>
                    </button>
                </div>
            `);
        },
    });
}

function clearRuleList() {
    $(".rule-item").remove();
    $(".rule-item-disabled").remove();
}

function appendToRuleList(itemData) {
    var name = itemData["is_active"] ? itemData["name"] : `${itemData["name"]} <i>(disabled)</i>`;
    var itemClass = itemData["is_active"] ? "rule-item" : "rule-item-disabled";

    $("#myRuleList").append(`
        <li class="list-group-item ${itemClass}"><a href="#" data-toggle="modal" data-target="#ruleModal" onclick="populateRuleModalBody(${itemData["id"]})">${name}</a></li>
    `);
}

function populateRuleList() {
    clearRuleList();

    $.getJSON(`/api/rules/`)
        .done(function(data) {
            $.each(data, function(i, x) {
                appendToRuleList(x);        
            });
        })
        .fail(function() {
            $("#myRuleList").append(`
                <li class="list-group-item rule-item-disabled"><a href="#" onclick="populateRuleList()">Failed to get rules. Click here to try again.</a></li>
            `);
        });
}

function logout() {
    $("#logoutButton").html(`
        <div class="spinner-border spinner-border-sm" role="status">
            <span class="sr-only">Logging out...</span>
        </div>
    `);

    $.ajaxSetup({
        headers: {"X-CSRFToken": getCSRF()}
    });

    $.ajax({
        type: "POST",
        url: "/api/logout/",
        success: function() {
            window.location.replace("/");
        },
        error: function() {
            $("#logoutButton").html("Logout");
            $("#accountModalBody").append(`
                <div class="alert alert-danger alert-dismissible fade show" role="alert">
                    There was an issue logging you out. Please try again.
                    <button type="button" class="close" data-dismiss="alert" aria-label="Close">
                        <span aria-hidden="true">&times;</span>
                    </button>
                </div>
            `);
        },
    });
}

function deleteAccount() {
    $("#deleteAccountButton").html(`
        <div class="spinner-border spinner-border-sm" role="status">
            <span class="sr-only">Deleting account...</span>
        </div>
    `);

    $.ajaxSetup({
        headers: {"X-CSRFToken": getCSRF()}
    });

    $.ajax({
        type: "DELETE",
        url: "/api/delete_account/",
        success: function() {
            window.location.replace("/");
        },
        error: function() {
            $("#deleteAccountButton").html("Delete account");
            $("#accountModalBody").append(`
                <div class="alert alert-danger alert-dismissible fade show" role="alert">
                    There was an issue deleting your account. Please try again.
                    <button type="button" class="close" data-dismiss="alert" aria-label="Close">
                        <span aria-hidden="true">&times;</span>
                    </button>
                </div>
            `);
        },
    });
}

$(document).ready(populateRuleList);
