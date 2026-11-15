import { Ticket } from "./Ticket";

export function Repairs({ jobs }: { jobs: { id: string; bike: string; due: string }[] }) {
  return (
    <section className="repairs">
      <h2 className="repairs-title">Bikes in the workshop today</h2>
      <ul className="repairs-list">
        {jobs.map((job) => (
          <li key={job.id}>
            <Ticket number={job.id} bike={job.bike} due={job.due} />
          </li>
        ))}
      </ul>
      <a href="/book">Book a service for Saturday</a>
    </section>
  );
}
