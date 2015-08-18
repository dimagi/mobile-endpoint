function(doc) {
    if(doc.doc_type == "CommCareCase") {
        emit([doc.domain, doc.owner_id, doc.closed], null);
    }
}
